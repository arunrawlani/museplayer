import sys
import signal
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from Muse_v2 import *
import struct
import json
import google.protobuf.internal.containers
import output_handler

# Catch Control-C interrupt and cancel
def ix_signal_handler(signum, frame):
    print "Aborted."
    sys.exit()


def CreateMuseFileReader(infile):
    # (1) Read the message header
    header_bin = infile.read(4)
    # check for EOF
    if len(header_bin) == 0:
        print "Zero Sized Muse File"
        exit()

    header = struct.unpack("<i", header_bin)
    msg_length = header[0]
    msg_type = infile.read(2)
    msg_type = struct.unpack("<h", msg_type)
    msg_type = msg_type[0]
    infile.seek(0, 0)
    if msg_type == 1:
        # set reader to version 1
        print "Version 1 not supported right now."
        #return MuseProtoBufReaderV1(verbose)
    elif msg_type == 2:
        # set reader to version 2
        return MuseProtoBufReaderV2(infile)


class MuseProtoBufReaderV2(object):

    def __init__(self, infile):
        self.events = []
        self.__config_id = 0
        self.__verbose = True
        self.__timestamp = 0
        self.added_to_events = 0
        self.infile = infile
        self.matlabWriter = None

    def setMatlabWriter(self, MatlabWriter):
        self.matlabWriter = MatlabWriter

    def parse(self):
        done = False
        while True:
            # (1) Read the message header
            header_bin = self.infile.read(4)
            # check for EOF
            if len(header_bin) == 0:
                break

            header = struct.unpack("<i", header_bin)
            msg_length = header[0]
            msg_type = self.infile.read(2)
            msg_type = struct.unpack("<h", msg_type)
            msg_type = msg_type[0]
            if msg_type != 2:
                print 'Corrupted file, type mismatch. Parsed: ' + str(msg_type) + ' expected 2'
                break

            # (2) Read and parse the message
            msg_bin = self.infile.read(msg_length)
            if len(msg_bin) != msg_length:
                print 'Corrupted file, length mismatch. Reporting length: ' + str(len(msg_bin)) + ' expected: ' + str(msg_length)
                break

            muse_data_collection = MuseDataCollection()
            muse_data_collection.ParseFromString(msg_bin)

            # (3) Process this chunk of data
            for obj in muse_data_collection.collection:
                self.handle_data(obj)
        self.add_done()

    def add_done(self):
        self.matlabWriter.receive_msg([self.__timestamp + 0.001, 'done'])

    # dispatch based on data type
    def handle_data(self, md):
        # Version 2 response
        # Configuration data
        self.__config_id = md.config_id
        if md.datatype == MuseData.CONFIG:
            data_obj = md.Extensions[MuseConfig.museData]
            json_dict = self.handle_json_dictionary_from_proto(data_obj)
            self.matlabWriter.receive_msg([md.timestamp, "/muse/config", "s", [str(json_dict)], self.__config_id])

        # Version
        if md.datatype == MuseData.VERSION:
            data_obj = md.Extensions[MuseVersion.museData]
            json_dict = self.handle_json_dictionary_from_proto(data_obj)
            self.matlabWriter.receive_msg([md.timestamp, "/muse/version", "s", [str(json_dict)], self.__config_id])

        # EEG samples
        if md.datatype == MuseData.EEG:
            data_obj = md.Extensions[EEG.museData]
            # Check if this is a DRL/REF message
            if data_obj.HasField("drl"):
                self.matlabWriter.receive_msg([md.timestamp, "/muse/drlref", "ff", [data_obj.drl, data_obj.ref], self.__config_id])
            else:
                data_count = len(data_obj.values)
                osc_type = 'f'*data_count
                self.matlabWriter.receive_msg([md.timestamp, "/muse/eeg", osc_type, data_obj.values, self.__config_id])

        # Quantization data
        if md.datatype == MuseData.QUANT:
            data_obj = md.Extensions[MuseQuantization.museData]
            data_count = len(data_obj.values)
            osc_type = 'i'*data_count
            self.matlabWriter.receive_msg([md.timestamp, "/muse/eeg/quantization", osc_type, data_obj.values, self.__config_id])

        # Accelerometer
        if md.datatype == MuseData.ACCEL:
            data_obj = md.Extensions[Accelerometer.museData]
            self.matlabWriter.receive_msg([md.timestamp, "/muse/acc", "fff",
                    [data_obj.acc1, data_obj.acc2, data_obj.acc3],
                    self.__config_id])

        # Battery
        if md.datatype == MuseData.BATTERY:
            data_obj = md.Extensions[Battery.museData]
            self.matlabWriter.receive_msg([md.timestamp, "/muse/batt", "iiii",
                      [data_obj.percent_remaining,
                       data_obj.battery_fuel_gauge_millivolts,
                       data_obj.battery_adc_millivolts,
                       data_obj.temperature_celsius], self.__config_id])

        # Annotations
        if md.datatype == MuseData.ANNOTATION:
            data_obj = md.Extensions[Annotation.museData]
            if data_obj.event_data_format == Annotation.OSC:
                temp = data_obj.event_data.split(" ")
                path = temp[0]
                osc_types = temp[1]
                string_data = temp[2:2+len(osc_types)]
                data = []
                i = 0
                for osc_type in osc_types:
                    if 'f' in osc_type:
                        data.append(float(string_data[i]))
                    elif 'i' in osc_type:
                        data.append(int(string_data[i]))
                    elif 'd' in osc_type:
                        data.append(float(string_data[i]))
                    elif 's' in osc_type:
                        data.append(str(string_data[i]))
                    i += 1
                self.matlabWriter.receive_msg([md.timestamp, path, osc_types, data, self.__config_id])
            else:
                event_format = ""
                if data_obj.event_data_format == Annotation.PLAIN_STRING:
                    event_format = "Plain String"
                elif data_obj.event_data_format == Annotation.JSON:
                    event_format = "JSON"
                self.matlabWriter.receive_msg([md.timestamp, "/muse/annotation", "sssss", [data_obj.event_data, event_format, data_obj.event_type, data_obj.event_id, data_obj.parent_id], self.__config_id])

        # DSP
        if md.datatype == MuseData.DSP:
            data_obj = md.Extensions[DSP.museData]
            data_count = len(data_obj.float_array)
            osc_type = 'f'*data_count
            self.matlabWriter.receive_msg([md.timestamp, "/muse/dsp/" + data_obj.type, osc_type, data_obj.float_array, self.__config_id])

        # ComputingDevice
        if md.datatype == MuseData.COMPUTING_DEVICE:
            data_obj = md.Extensions[ComputingDevice.museData]
            json_dict = self.handle_json_dictionary_from_proto(data_obj)
            self.matlabWriter.receive_msg([md.timestamp, "/muse/device", "s", [str(json_dict)], self.__config_id])

        # EEG Dropped
        if md.datatype == MuseData.EEG_DROPPED:
            data_obj = md.Extensions[EEG_DroppedSamples.museData]
            self.matlabWriter.receive_msg([md.timestamp, "/muse/eeg/dropped", "i", [data_obj.num], self.__config_id])

        # Acc Dropped
        if md.datatype == MuseData.ACC_DROPPED:
            data_obj = md.Extensions[ACC_DroppedSamples.museData]
            self.matlabWriter.receive_msg([md.timestamp, "/muse/acc/dropped", "i", [data_obj.num], self.__config_id])

    def handle_json_dictionary_from_proto(self, data_obj):
        m = {}
        for a in dir(data_obj):
            upperFlag = False
            if a.startswith('_'):
                continue
            for x in a:
                if x.isupper():
                    upperFlag = True
                    break
            if upperFlag:
                continue
            value = getattr(data_obj,a)
            if isinstance(value, google.protobuf.internal.containers.RepeatedScalarFieldContainer):
                temp = []
                temp.extend(value)
                value = temp
            m[a] = value

        return json.dumps(m)



def run():
    # Catch control-C
    signal.signal(signal.SIGINT, ix_signal_handler)

    parser = ArgumentParser(description="Coverts .muse files to .mat files.",
                            prog="muse-to-mat.py",
                            usage="%(prog)s -i <input_file> -o <output_file>",
                            formatter_class=RawDescriptionHelpFormatter,
                            epilog="""

Examples:
    muse-to-mat.py -i input.muse -o output.mat
        This will read in the file "input.muse" and create a file "output.mat" with the converted data in it.

                            """)
    parser.add_argument("-i", "--input-muse-file",
                              help="Input Muse file",
                              metavar="FILE")
    parser.add_argument("-o", "--output-mat-file",
                              help="Output MATLAB file",
                              metavar="FILE")
    parser.add_argument("-v", "--verbose", const="verbose", nargs="?", help="Print some output.")
    args = parser.parse_args()

    if not args.input_muse_file or not args.output_mat_file:
        print "Not enough args."
        sys.exit()

    infile = None
    try:
        infile = open(args.input_muse_file, "rb")
    except:
        print "File not found: " + args.input_muse_file
        exit()

    if args.verbose:
        print "File opened: " + args.input_muse_file

    reader = CreateMuseFileReader(infile)
    matlab_writer = output_handler.MatlabWriter(args.output_mat_file)
    matlab_writer.set_data_structure()
    reader.setMatlabWriter(matlab_writer)
    reader.parse()
    if args.verbose:
        print "MATLAB file written: " + args.output_mat_file

if __name__ == "__main__":
    run()

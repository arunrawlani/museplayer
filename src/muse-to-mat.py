import sys
import signal
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from Muse_v2 import *
import struct
import json
import google.protobuf.internal.containers
import hdf5storage as h5
import numpy as np
import re

# Catch Control-C interrupt and cancel
def ix_signal_handler(signum, frame):
    print "Aborted."
    sys.exit()


def CreateMuseFileReader(infile, verbose=True):
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
    if verbose:
        print 'Muse File version #' + str(msg_type)
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
                done = True
                break

            header = struct.unpack("<i", header_bin)
            msg_length = header[0]
            msg_type = self.infile.read(2)
            msg_type = struct.unpack("<h", msg_type)
            msg_type = msg_type[0]
            if msg_type != 2:
                print 'Corrupted file, type mismatch. Parsed: ' + str(msg_type) + ' expected 2'
                done = True
                break

            # (2) Read and parse the message
            msg_bin = self.infile.read(msg_length)
            if len(msg_bin) != msg_length:
                print 'Corrupted file, length mismatch. Reporting length: ' + str(len(msg_bin)) + ' expected: ' + str(msg_length)
                done = True
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
                #print [md.timestamp, "/muse/eeg", osc_type, data_obj.values, self.__config_id]
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

class MatlabWriter():
    def __init__(self, out_file):
        # the most important part of dataset is now the first dict which contains the main struct, IXDATA
        self.__dataset = {}
        self.set_data_structure()
        self.__value = []
        self.__file_out = out_file
        self.received_data = 0
        self.data_written = 0
        self.files_written = 0
        self.__verbose = None
        self.__filters = None

    @staticmethod
    def path_contains_filter(filters, type):
        if filters == None:
            return True
        else:
            for filter in filters:
                if re.search(filter, type):
                    return True
        return False

    def set_data_structure(self, config = {}, device = {}):
        self.__dataset = {
            u'IXDATA': {
                u'sessionID': [],
                u'muse': [],
                u'raw': {
                    u'eeg': {
                        u'times': [],
                        u'data': [],
                        u'quantization_times': [],
                        u'quantization': [],
                        u'dropped_times': [],
                        u'dropped': []
                        },
                    u'acc': {
                        u'times': [],
                        u'data': [],
                        u'dropped_times': [],
                        u'dropped': []
                    },
                    u'battery': {
                        u'val': [],
                        u'times': []
                    },
                    u'drlref': {
                        u'times': [],
                        u'data': []
                    }
                },
                u'm_struct': {
                    u'm_names': [],
                    u'i_names': [],
                    u'm_times': [],
                    u'i_times': []
                },
                u'feat': [],
                u'class': []
            },
            u'config': {}, #config data
            u'device': {}, #computing device data
        }

    def set_options(self, verbose, filters):
        self.__verbose = verbose
        self.__filters = filters

    def write_array(self):
        #print self.__dataset
        # Check if there is anything to save
        if len(self.__dataset['config']) == 0:
            self.__dataset['config'] = [['config'], 'missing']
        if len(self.__dataset['device']) == 0:
            self.__dataset['device'] = [['device'], 'missing']

        file_name = self.__file_out
        if self.files_written:
            if '.mat' in self.__file_out[len(self.__file_out)-4:len(self.__file_out)]:
                file_name = self.__file_out[0:len(self.__file_out)-4] + '_' + str(self.files_written+1)
            else:
                file_name = self.__file_out + '_' + str(self.files_written+1)

        self.__dataset['IXDATA'] = self.convert_list_to_numpy_list(self.__dataset['IXDATA'])
        if 'elements' in self.__dataset:
            self.__dataset['elements'] = self.convert_list_to_numpy_list(self.__dataset['elements'])
        h5.write(self.__dataset, path='/', filename=file_name,  truncate_existing=True, store_python_metadata=True, matlab_compatible=True)

        self.files_written += 1

    def convert_list_to_numpy_list(self, dictionary):
        if not dictionary:
            return dictionary
        if isinstance(dictionary, dict):
            for key, value in dictionary.iteritems():
                if key in ['m_names', 'i_names']:
                    continue
                if isinstance(value, dict):
                    diction = self.convert_list_to_numpy_list(value)
                    dictionary[key] = diction
                elif isinstance(value, list):
                    dictionary[key] = np.array(value)
            return dictionary

    def handle_raw_data(self, osc_path, input_data):
            eeg_data_identifier = ["eeg/quantization", "eeg/dropped", "eeg"]
            acc_data_identifier = ["acc/dropped", "acc"]
            drlref_data_identifier = ["drlref"]
            battery_data_identifier = ["muse/batt"]

            if any(identifier in osc_path for identifier in eeg_data_identifier):
                type_key = "eeg"
                if "eeg/quantization" in osc_path:
                    time_key = "quantization_times"
                    data_key = "quantization"
                elif "eeg/dropped" in osc_path:
                    time_key = "dropped_times"
                    data_key = "dropped"
                elif "eeg" in osc_path:
                    time_key = "times"
                    data_key = "data"
            elif any(identifier in osc_path for identifier in acc_data_identifier):
                type_key = "acc"
                if "acc/dropped" in osc_path:
                    time_key = "dropped_times"
                    data_key = "dropped"
                elif "acc" in osc_path:
                    time_key = "times"
                    data_key = "data"
            elif any(identifier in osc_path for identifier in drlref_data_identifier):
                type_key = "drlref"
                time_key = "times"
                data_key = "data"
            elif any(identifier in osc_path for identifier in battery_data_identifier):
                type_key = "battery"
                time_key = "times"
                data_key = "val"

            self.__dataset['IXDATA']["raw"][type_key][time_key].append([input_data[0]])
            data = []
            for x in input_data[1:]:
                data.append(float(x))
            self.__dataset['IXDATA']["raw"][type_key][data_key].append(data)

    def handle_config_data(self, osc_path, input_data):
            old_format_offset = 6
            if "muse/config" in osc_path or "muse/version" in osc_path:
                key = "config"
                if "muse/config" in osc_path:
                    old_format_offset = 13
            elif "muse/device" in osc_path:
                key = "device"
            try:
                data = json.loads(input_data[1])
                for item in data:
                    if isinstance(data[item], unicode):
                        output_data = str(data[item])
                    else:
                        output_data = np.array(data[item])
                    self.__dataset[key][unicode(item)] = [np.array(input_data[0]), output_data]
            except:
                datatype = osc_path[old_format_offset:]
                self.__dataset[key][unicode(datatype)] = [[input_data[0]], input_data[1]]

    def create_dict_based_on_path(self, dictionary, path_list, dataset):
        if len(path_list) == 1:
            dictionary.setdefault(unicode(path_list[0]), []).append(dataset)
            return dictionary
        else:
            dictionary[unicode(path_list[0])] = self.create_dict_based_on_path(dictionary.setdefault(unicode(path_list[0]), {}), path_list[1:], dataset)
            return dictionary

    def receive_msg(self, msg):
        raw_data_identifier = ["eeg/quantization", "eeg/dropped", "eeg", "acc/dropped", "acc", "drlref", "muse/batt"]
        config_identifier = ["muse/config", "muse/version", "muse/device"]
        if "done" in msg:
            self.write_array()
            return

        temp = []
        temp.append(msg[0])
        i = 1
        for x in msg[3]:
            temp.append(x)
            i = i + 1
        if ('i' in msg[2]) or ('f' in msg[2]) or ('d' in msg[2]) or ('s' in msg[2]):
            if any(identifier in msg[1] for identifier in raw_data_identifier):
                self.handle_raw_data(msg[1], temp)
            elif any(identifier in msg[1] for identifier in config_identifier):
                self.handle_config_data(msg[1], temp)
            elif "muse/annotation" in msg[1]:
                if (re.search('Start$', temp[1]) or re.search('BEGIN$', temp[1])) and not ('Click' in temp[1]) and not ('Session' in temp[1]):
                    self.__dataset["IXDATA"]["m_struct"]["m_names"].append([str(temp[1][8:len(temp[1])-6])])
                    self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 0])
                elif re.search('Stop$', temp[1]) or re.search("Done$", temp[1]) or re.search("END$", temp[1]):
                    self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 1])
                elif len(temp) > 3:
                    if 'instance' in temp[3]:
                        self.__dataset["IXDATA"]["m_struct"]["i_names"].append([str(temp[1][1:])])
                        self.__dataset["IXDATA"]["m_struct"]["i_times"].append([temp[0]])
                    elif 'begin' in temp[3]:
                        self.__dataset["IXDATA"]["m_struct"]["m_names"].append([str(temp[1][8:])])
                        self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 0])
                    elif 'end' in temp[3]:
                        self.__dataset["IXDATA"]["m_struct"]["m_times"].append([temp[0], 1])
                    else:
                        self.__dataset["IXDATA"]["m_struct"]["i_names"].append([unicode(temp[1])])
                        self.__dataset["IXDATA"]["m_struct"]["i_times"].append([temp[0]])
                else:
                    self.__dataset["IXDATA"]["m_struct"]["i_names"].append([str(temp[1])])
                    self.__dataset["IXDATA"]["m_struct"]["i_times"].append([temp[0]])
            elif "/muse/elements" in msg[1]:
                msg[1] = msg[1].replace('-', '_')
                name = msg[1][15:].replace('/', '_')
                self.__dataset.setdefault(u'elements', {}).setdefault(unicode(name), []).append(temp)
        else:
            if self.__verbose:
                print "Unknown Data ", msg[1], " ", msg[2], " ", msg[3]

        self.received_data += 1
        self.data_written += 1
        if self.received_data > 36000*30: #Approximately 1 minutes at 500Hz * 30 for 30 minutes files
            self.write_array()
            self.received_data = 0


def run():
    # Catch control-C
    signal.signal(signal.SIGINT, ix_signal_handler)

    parser = ArgumentParser(description="woo",
                            prog="muse-to-mat.py",
                            usage="%(prog)s -i <input_file> -o <output_file>",
                            formatter_class=RawDescriptionHelpFormatter,
                            epilog="""

Examples:
    muse-to-mat -i input.muse -o output.mat
        This will read in the file "my_eeg_recording.muse" and send those messages as OSC to port 7887.

                            """)

    parser.add_argument("-i", "--input-muse-file",
                              help="Input Muse file",
                              metavar="FILE")

    parser.add_argument("-o", "--output-mat-file",
                              help="Output MATLAB file",
                              metavar="FILE")

    args = parser.parse_args()

    try:
        infile = open(args.input_muse_file, "rb")
    except:
        print "File not found: " + args.input_muse_file
        exit()

    print "File opened: " + args.input_muse_file

    reader = CreateMuseFileReader(infile)
    matlabWriter = MatlabWriter(args.output_mat_file)
    matlabWriter.set_data_structure()
    reader.setMatlabWriter(matlabWriter)
    reader.parse()

    print args.output_mat_file

if __name__ == "__main__":
    run()

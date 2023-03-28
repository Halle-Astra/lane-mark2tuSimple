import os
import xml.etree.ElementTree as ET
import json
from lxml import etree
from argparse import ArgumentParser
import numpy as np


def xml2dict_recursively_by_node(node):
    if not isinstance(node, ET.Element):
        raise Exception("node format error.")

    if len(node) == 0:
        return node.tag, node.text

    data = {}
    temp = None
    for child in node:
        key, val = xml2dict_recursively_by_node(child)
        if key in data:
            if type(data[key]) == list:
                data[key].append(val)
            else:
                temp = data[key]
                data[key] = [temp, val]
        else:
            data[key] = val

    return node.tag, data


def xml2dict_byfile(file):
    tree = ET.parse(file)
    node = tree.getroot()
    tag, data_dict = xml2dict_recursively_by_node(node)
    return data_dict


def xmls2tuSimple(annotation_files, coorY: list or dict):
    if isinstance(coorY, dict):  # I will assume the coorY passed by the configuration.
        coorY = getCoorY(config)
    for annotation_file in annotation_files:
        data_tuSimple = xml2tuSimple_single_file(annotation_file, coorY)
        jsonify_data_tuSimple(data_tuSimple)
        print(annotation_file, "is jsonified as tuSimple format.")


def xml2tuSimple_single_file(annotation_file, coorY: list):
    lanes_data = xml2dict_byfile(annotation_file)
    data_tuSimple = dict()

    # for raw_file
    annotation_path = os.path.join(lanes_data['folder'],
                                   lanes_data['filename'])
    data_tuSimple['raw_file'] = annotation_file

    # for lanes and h_samples
    lanes = lanes_data['object']
    tuSimple_unifier = TuSimple_Unifier(coorY)
    lanes_tuSimple = tuSimple_unifier(lanes)
    data_tuSimple['lanes'] = lanes_tuSimple
    data_tuSimple['h_samples'] = coorY

    return data_tuSimple


def jsonify_data_tuSimple(data_tuSimple):
    aim_path = data_tuSimple['raw_file'].replace(".xml", ".json")
    f = open(aim_path, 'w')
    json.dump(data_tuSimple, f)
    f.close()


def getConfig(config_path):
    json_f = open(config_path)
    json_content = json.load(json_f)
    json_f.close()
    return json_content


def getCoorY(configure: dict):
    y = list(range(configure['y_min'],
                   configure['y_max'],
                   configure['interval']))
    if configure['include_y_max']:
        y_max_python = configure['y_max'] - 1
        if y_max_python not in y:
            y.append(y_max_python)
    return y


class TuSimple_Unifier:
    def __init__(self, coorY):
        """
        The class for transforming the lanes in xml format into the format of tuSimple.
        :param coorY: h_samples in tuSimple format
        """
        if not isinstance(coorY, np.ndarray):
            coorY = np.array(coorY)
        self.h_samples = coorY

    def __call__(self, lane, *args, **kwargs):
        """
        will transform the lanes in xml format into the format of tuSimple. The input must be the direct output of the xml file parsing.
        :param lane: the lane points, the element output of the xml parsing. If this param passed as multiple lanes, it also will be processed in the same way of only one lane.
        :param args:
        :param kwargs:
        :return: x coordinates, list of list
        """
        if not isinstance(lane, list):
            lanes = [lane]
        else:
            lanes = lane
        lines_tuSimple = []
        for lane_ in lanes:
            ## calc the important params, especially the positions where need to be interpolated
            lane_points = lane_["polyline"]["points"]
            lane_points = self.points_string2ndarary(lane_points)
            x_lane = lane_points[:, 0]
            y_lane = lane_points[:, 1]
            y_min_lane = np.min(y_lane)
            y_max_lane = np.max(y_lane)
            h_samples_isNeedInterpolated = (self.h_samples >= y_min_lane) & (self.h_samples <= y_max_lane)
            h_samples_needInterpolated = self.h_samples[h_samples_isNeedInterpolated]
            # x_interpolated = np.interp(h_samples_needInterpolated, y_lane, x_lane) # 这个方法对于非可逆函数会得到全部有问题的点

            ## Interpolation by sub-lines, avoiding the problem of non-invertable curve interpolation
            x_interpted_ls = []
            for h in h_samples_needInterpolated:
                above_y = y_lane[y_lane <= h]
                below_y = y_lane[y_lane >= h]
                below_y_start_position = np.sum(y_lane < h)
                close_above_y_position = np.argmin(np.abs(above_y - h))
                close_below_y_position = np.argmin(np.abs(below_y - h)) + below_y_start_position
                close_above_y = y_lane[close_above_y_position]
                close_above_x = x_lane[close_above_y_position]
                close_below_y = y_lane[close_below_y_position]
                close_below_x = x_lane[close_below_y_position]
                x_interpted = np.interp(h, [close_above_y, close_below_y], [close_above_x, close_below_x])
                x_interpted = float(x_interpted)
                x_interpted_ls.append(x_interpted)

            ## compensate for other h_samples
            head_nums = h_samples_isNeedInterpolated.tolist().index(True)
            tail_nums = self.h_samples.__len__() - head_nums - np.sum(h_samples_needInterpolated)
            x_interpted_ls = [-2] * head_nums + x_interpted_ls + [-2] * tail_nums

            lines_tuSimple.append(x_interpted_ls)
        return lines_tuSimple

    def points_string2ndarary(self, points_string):
        points = points_string.split(";")
        points = [[eval(ii) for ii in i.split(",")] for i in points]
        points_ndarray = np.array(points)
        return points_ndarray


def interpolate_as_sublines(x_lane, y_lane, coorY):
    """The core algorithm in this script, interpolation in the way of sub-lines!"""
    y_min_lane = np.min(y_lane)
    y_max_lane = np.max(y_lane)
    h_samples_isNeedInterpolated = (coorY >= y_min_lane) & (coorY <= y_max_lane)
    h_samples_needInterpolated = coorY[h_samples_isNeedInterpolated]
    # x_interpolated = np.interp(h_samples_needInterpolated, y_lane, x_lane) # 这个方法对于非可逆函数会得到全部有问题的点

    ## Interpolation by sub-lines, avoiding the problem of non-invertable curve interpolation
    x_interpted_ls = []
    for h in h_samples_needInterpolated:
        above_y = y_lane[y_lane <= h]
        below_y = y_lane[y_lane >= h]
        below_y_start_position = np.sum(y_lane < h)
        close_above_y_position = np.argmin(np.abs(above_y - h))
        close_below_y_position = np.argmin(np.abs(below_y - h)) + below_y_start_position
        close_above_y = y_lane[close_above_y_position]
        close_above_x = x_lane[close_above_y_position]
        close_below_y = y_lane[close_below_y_position]
        close_below_x = x_lane[close_below_y_position]
        x_interpted = np.interp(h, [close_above_y, close_below_y], [close_above_x, close_below_x])
        x_interpted = float(x_interpted)
        x_interpted_ls.append(x_interpted)
    return x_interpted_ls


### self-test part
if __name__ == "__main__":
    args = ArgumentParser()
    args.add_argument("--config", "-c", type=str,
                      default="coorY_config.json",
                      help="The configuration file.")
    args.add_argument("--input", "-i", type=str,
                      default="factory_in_1_1.xml",
                      help="Can be the folder or only the path of one file")
    args = args.parse_args()
    config = getConfig(args.config)

    if os.path.isfile(args.input):
        files = [args.input]
    elif os.path.isdir(args.input):
        files = os.listdir(args.input)
        files = [os.path.join(args.input, i) for i in files if i.endswith(".xml")]

    xmls2tuSimple(files, config)

    # only for test the core algorithm!
    from matplotlib import pyplot as plt

    x = np.arange(-10, 10, 0.01)
    y = x ** 2 - 15 * np.sin(x)
    y1 = np.arange(20, 80)
    x1 = interpolate_as_sublines(y,x,y1)
    plt.plot(x, y)
    plt.plot(x1, y1)
    plt.show()

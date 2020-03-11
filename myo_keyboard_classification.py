import collections
import math

from input_files_reader import \
    backward_orientation, backward_accelerometer, backward_gyro, backward_timestamps, \
    forward_accelerometer, forward_gyro, forward_orientation, forward_timestamps, \
    left_accelerometer, left_gyro, left_orientation, left_timestamps, \
    right_accelerometer, right_gyro, right_orientation, right_timestamps, \
    enter_accelerometer, enter_gyro, enter_orientation, enter_timestamps

import tensorflow as tf
import pandas as pd
import copy
import numpy as np
from typing import List


# backward_gyro = pd.read_csv('Myo Keyboard Data/Backward/gyro-1456704054.csv')
# # print(type(backward_gyro['x']))
# timestamp = backward_gyro['timestamp'].to_frame()
# times = []
# maxes = []
# x_col = copy.deepcopy(backward_gyro['x'])
# indices = [i for i in range(len(x_col))]
# # x_col.reindex(indices)
# num_rows = len(x_col)
# x_col = x_col.to_frame()
# x_col = x_col.drop([i for i in range(100)])
# x_col = x_col.drop([i for i in range(num_rows-90, num_rows)])
# x_col = np.array_split(x_col, 10)
#
# print("***" + str(type(x_col[0])))


# extract the periods of time with no change in all three axes z, y and z
def extract_nochange_periods(timestamp, x, y, z):
    periods = []
    i = 0
    while i < len(timestamp) - 3:
        if x[i + 1] == x[i] and y[i + 1] == y[i] and z[i + 1] == z[i]:
            periods.append(timestamp[i])
            i += 3
        else:
            i += 1
    return periods


def create_ten_groups(peak: float, timestamps: List, accelerometer: dict) -> List:
    groups = []
    for i in range(len(timestamps) - 1):
        starting_position = accelerometer['timestamp'].index(timestamps[i])
        ending_position = accelerometer['timestamp'].index(timestamps[i + 1])
        while starting_position < ending_position:
            if accelerometer['y'][starting_position] < peak:
                groups.append((timestamps[i], timestamps[i + 1]))
                break
            starting_position += 1

    while len(groups) > 10:  # remove the first element until size is 10
        groups = groups[1:]
    while len(groups) < 10:
        groups.append(groups[len(groups) - 2])

    return groups


def extract_data_to_ten_groups(orientation: dict, accelerometer: dict):
    orientation_nochange_timestamps = extract_nochange_periods(orientation['timestamp'],
                                                               orientation['x'], orientation['y'], orientation['z'])
    return create_ten_groups(sorted(accelerometer['y'])[30], orientation_nochange_timestamps, accelerometer)


def find_existing_timestamp_group_average_lengths(groups: List, timestamps: List) -> int:
    length = 0
    for i in range(len(groups)):
        for j in range(len(timestamps)):
            if float(groups[i][0]) <= float(timestamps[j]) < float(groups[i][1]):
                length += 1
    return int(length / len(groups))


def normalize_groups(groups: List, expected_group_len: int, timestamps: List, given_data: List) -> List:
    normalized_groups = []
    for i in range(len(groups)):
        curr_max, curr_max_index = 0.0, 0
        for j in range(len(timestamps)):
            if float(groups[i][0]) <= float(timestamps[j]) < float(groups[i][1]):
                # curr_max = max(curr_max, float(given_data[j]))
                if float(given_data[j]) > curr_max:
                    curr_max = float(given_data[j])
                    curr_max_index = j
        # make sure the groups have the same size
        normalized_groups.append((timestamps[curr_max_index - int(expected_group_len / 2)],
                                  timestamps[curr_max_index + int(expected_group_len / 2)]))
    return normalized_groups


# data being accelerometer, gyro or orientation
# type is either gyro, accelerometer and axis is either x, y or z
def pre_process_data(info_type: str, axis: str) -> ():
    backward_groups = extract_data_to_ten_groups(backward_orientation, backward_accelerometer)
    forward_groups = extract_data_to_ten_groups(forward_orientation, forward_accelerometer)
    left_groups = extract_data_to_ten_groups(left_orientation, left_accelerometer)
    right_groups = extract_data_to_ten_groups(right_orientation, right_accelerometer)
    enter_groups = extract_data_to_ten_groups(enter_orientation, enter_accelerometer)

    mean_group_length_all_labels = \
        math.floor((find_existing_timestamp_group_average_lengths(backward_groups, backward_timestamps) +
                    find_existing_timestamp_group_average_lengths(forward_groups, forward_timestamps) +
                    find_existing_timestamp_group_average_lengths(left_groups, left_timestamps) +
                    find_existing_timestamp_group_average_lengths(right_groups, right_timestamps) +
                    find_existing_timestamp_group_average_lengths(enter_groups, enter_timestamps)) / 5)

    if info_type == 'gyro':
        backward_groups = normalize_groups(backward_groups, mean_group_length_all_labels,
                                           backward_timestamps, backward_gyro[axis])
        forward_groups = normalize_groups(forward_groups, mean_group_length_all_labels,
                                          forward_timestamps, forward_gyro[axis])
        left_groups = normalize_groups(left_groups, mean_group_length_all_labels, left_timestamps, left_gyro[axis])
        right_groups = normalize_groups(right_groups, mean_group_length_all_labels, right_timestamps, right_gyro[axis])
        enter_groups = normalize_groups(enter_groups, mean_group_length_all_labels, enter_timestamps, enter_gyro[axis])
    elif info_type == 'accelerometer':
        backward_groups = normalize_groups(backward_groups, mean_group_length_all_labels,
                                           backward_timestamps, backward_accelerometer[axis])
        forward_groups = normalize_groups(forward_groups, mean_group_length_all_labels,
                                          forward_timestamps, forward_accelerometer[axis])
        left_groups = normalize_groups(left_groups, mean_group_length_all_labels, left_timestamps,
                                       left_accelerometer[axis])
        right_groups = normalize_groups(right_groups, mean_group_length_all_labels, right_timestamps,
                                        right_accelerometer[axis])
        enter_groups = normalize_groups(enter_groups, mean_group_length_all_labels, enter_timestamps,
                                        enter_accelerometer[axis])
    return backward_groups, forward_groups, left_groups, right_groups, enter_groups, mean_group_length_all_labels


# get the actual data in the right data set and put them in pre-defined groups
def get_data_by_groups(groups: List[tuple], info_type: str, axis: str, given_data: dict, timestamps: List) -> List:
    actual_data = []
    if info_type == 'gyro':
        for i in range(len(groups)):
            actual_data.append(given_data[axis][timestamps.index(groups[i][0]): timestamps.index(groups[i][1])])
    elif info_type == 'accelerometer':
        for i in range(len(groups)):
            actual_data.append(given_data[axis][timestamps.index(groups[i][0]): timestamps.index(groups[i][1])])
    return actual_data


def standardize_groups_by_length(data: List, standard_length: int) -> List:
    standardized_groups = copy.deepcopy(data)
    for i in range(len(standardized_groups)):
        difference = standard_length - len(standardized_groups[i])
        if difference < 0:
            while len(standardized_groups[i]) != standard_length:
                standardized_groups[i].pop(-1)
        elif difference > 0:
            while len(standardized_groups[i]) != standard_length:
                standardized_groups[i].append('0.0')
    return standardized_groups


# axis being x, y or z
def process_single_axis(info_type: str, axis: str):
    result, data, labels = [], [], []  # labels being the expected/ground truth output
    backward_groups, forward_groups, left_groups, right_groups, enter_groups, mean_group_length_all_labels \
        = pre_process_data(info_type, axis)
    backward_chosen_data, forward_chosen_data = [], []
    left_chosen_data, right_chosen_data, enter_chosen_data = [], [], []
    print('Getting {} data of axis {}...'.format(info_type, axis))

    if info_type == 'gyro':
        backward_chosen_data = get_data_by_groups(backward_groups, info_type, axis, backward_gyro,
                                                  backward_timestamps)
        forward_chosen_data = get_data_by_groups(forward_groups, info_type, axis, forward_gyro, forward_timestamps)
        left_chosen_data = get_data_by_groups(left_groups, info_type, axis, left_gyro, left_timestamps)
        right_chosen_data = get_data_by_groups(right_groups, info_type, axis, right_gyro, right_timestamps)
        enter_chosen_data = get_data_by_groups(enter_groups, info_type, axis, enter_gyro, enter_timestamps)
    elif info_type == 'accelerometer':
        backward_chosen_data = get_data_by_groups(backward_groups, info_type, axis, backward_accelerometer,
                                                  backward_timestamps)
        forward_chosen_data = get_data_by_groups(forward_groups, info_type, axis, forward_accelerometer,
                                                 forward_timestamps)
        left_chosen_data = get_data_by_groups(left_groups, info_type, axis, left_accelerometer, left_timestamps)
        right_chosen_data = get_data_by_groups(right_groups, info_type, axis, right_accelerometer, right_timestamps)
        enter_chosen_data = get_data_by_groups(enter_groups, info_type, axis, enter_accelerometer, enter_timestamps)

    for i in range(len(backward_chosen_data)):
        data.append(forward_chosen_data[i])
        data.append(backward_chosen_data[i])
        data.append(left_chosen_data[i])
        data.append(right_chosen_data[i])
        data.append(enter_chosen_data[i])
        # data.append([forward_chosen_data[i]])
        # data.append([backward_chosen_data[i]])
        # data.append([left_chosen_data[i]])
        # data.append([right_chosen_data[i]])
        # data.append([enter_chosen_data[i]])
        labels.append([1, 0, 0, 0, 0])
        labels.append([0, 1, 0, 0, 0])
        labels.append([0, 0, 1, 0, 0])
        labels.append([0, 0, 0, 1, 0])
        labels.append([0, 0, 0, 0, 1])

    data = standardize_groups_by_length(data, mean_group_length_all_labels)

    for i in range(len(data)):
        # first item of a pair is the data, second item is the correct label
        pair = [list(map(float, data[i])), labels[i]]
        # pair = [list(map)]
        result.append(tuple(pair))

    return result, labels


# process all axes of the given info type
def process_multi_axes(info_type: str):
    print('Getting data from all three axes x, y and z...')
    result = []
    data_x = process_single_axis(info_type, 'x')[0]
    data_y = process_single_axis(info_type, 'y')[0]
    data_z, label = process_single_axis(info_type, 'z')
    combinations = []
    for i in range(len(data_x)):
        combinations.append(data_x[i][0] + data_y[i][0] + data_z[i][0])
    for i in range(len(combinations)):
        result.append([combinations[i], label[i]])
    return result
# groups = extract_data_to_ten_groups(backward_orientation, backward_accelerometer)
# print()
"""
for frame_num in range(0, len(x_col)):
    maxes.append(x_col[frame_num].max())
    i = x_col[frame_num].idxmax().x
    times.append(timestamp.iloc[i, :])
"""
# x_col = pd.Series(data=x_col, )
# the ten maxes for backward gyro are: 1456704056461410,
# for _ in range(10):
#     print(0)
#     maxes.append(x_col.max())
#     # print(x_col[x_col == maxes[-1]].index)
#     # print()
#     # i = x_col[x_col == maxes[-1]]
#     # i = i.index.values[0]
#     i = x_col.idxmax().x
#     times.append(timestamp.iloc[i, :])
#     neighbour_indices = [item for item in range(i-35, i+35)]
#     # print(neighbour_indices)
#     for row in neighbour_indices:
#         if (x_col.index == row).any():
#             x_col = x_col.drop([row])
#     # x_col = x_col[x_col != maxes[-1]]
#     # x_col.drop(labels=[])
# print(maxes)
# print(times)
# x_col

# print(tf.__version__)

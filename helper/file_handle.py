import os
import shutil

from color_format_display import UseStyle


def get_all_filenames(dir_path):
    filenames_list = []
    for root, dirs, files in os.walk(dir_path):
        for i in files:
            filenames_list.append(root + '\\' + i)
    print UseStyle(('Under this dir -- {dir}: There are {num} files ').format(dir=dir_path, num=len(filenames_list)),
             fore='purple')
    return filenames_list


def filter_file_by_suffixation(dir_path, *keySuffixation):
    file_name_list = get_all_filenames(dir_path)
    file_contain_suffixation = []
    for file in file_name_list:
        if os.path.splitext(file)[1] in tuple(keySuffixation):
            file_contain_suffixation.append(file)
    print UseStyle(('Under this dir -- {dir}: There are {num} files, suffix called {key}').format(dir=dir_path, num=len(
        file_contain_suffixation), key=keySuffixation), fore='purple')
    return file_contain_suffixation


def count_file_lines(file):
    num_col = 0
    if os.path.exists(file):
        with open(file, 'r') as fileWriter:
            while (fileWriter.readline() != ''):
                num_col = num_col + 1
        return num_col


def get_MD5(file_path):
    '''Verify MD5 to determine that the files in one are different from those in another'''
    files_md5 = os.popen('md5 %s' % file_path).read().strip()
    file_md5 = files_md5.replace('MD5 (%s) = ' % file_path, '')
    return file_md5


def copy_search_file(source_dir, target_dir):
    '''Only copy the source files to the target file'''
    if not os.path.exists(source_dir):
        raise Exception('No such source_dir !!!')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for file in os.listdir(source_dir):
        source_file = os.path.join(source_dir, file)
        target_file = os.path.join(target_dir, file)
        if os.path.isfile(source_file):
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            if not os.path.exists(target_file) or (
                    os.path.exists(target_file) and (os.path.getsize(target_file) != os.path.getsize(source_file))):
                open(target_file, "w").write(open(source_file, "r").read())
            if os.path.isdir(source_file):
                copy_search_file(source_file, target_file)


def copy_search_dir_and_file(source_dir, target_dir):
    '''Copy the source directory and files to the target file'''
    if not os.path.exists(source_dir):
        raise Exception('No such source_dir !!!')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for files in os.listdir(source_dir):
        source_file = os.path.join(source_dir, files)
        target_file = os.path.join(target_dir, files)
        if os.path.isfile(source_file):
            if os.path.isfile(target_file):
                if get_MD5(source_file) != get_MD5(target_file):
                    shutil.copy(source_file, target_file)
            else:
                shutil.copy(source_file, target_file)
        else:
            if not os.path.isdir(target_file):
                os.makedirs(target_file)
            copy_search_dir_and_file(source_file, target_file)

from ensurepip import version
import zlib
import subprocess
import os

class Git:

    testContent = 'Test' * 100

    def __init__(self, testFileName) -> None:
        self.testFileName = testFileName
        self.gitDirectoryName = 'git'
    
    def _initialize_git_directory(self):
        process_create_git = subprocess.Popen(['git', 'init', './' + self.gitDirectoryName], stdout=subprocess.PIPE)
        return process_create_git

    def _create_test_file_with_content(self, content):
        relativeFilePath = os.path.join(self.gitDirectoryName, self.testFileName)
        with open(relativeFilePath, 'w') as fl:
            fl.write(content)
    
    def _append_test_file_with_content(self, content):
        relativeFilePath = os.path.join(self.gitDirectoryName, self.testFileName)
        with open(relativeFilePath, 'a') as fl:
            fl.write(content)

    def pack_files(self, windowSize=10, deltaDepth=50):
        if deltaDepth>4095:
            raise('deltaDepth is too high!')
        process_pack = subprocess.Popen(['git', '-C', './' + self.gitDirectoryName,
                                         'pack-objects', f'--window={windowSize}',
                                         f'--depth={deltaDepth}'],
                                         stdout=subprocess.PIPE)
        return process_pack

    def git_clone(self):
        process_gc = subprocess.Popen(['git', '-C', './' + self.gitDirectoryName,
                                         'gc', '--aggressive'],
                                         stdout=subprocess.PIPE)
        return process_gc


    def _add_test_file_to_git(self):
        process_add_and_commit = subprocess.Popen(['git', '-C', './' + self.gitDirectoryName, 'add', self.testFileName], stdout=subprocess.PIPE)
        return process_add_and_commit


    def _commit_with_message(self, message):
        process_add_and_commit = subprocess.Popen(['git', '-C', './' + self.gitDirectoryName, 'commit', '-m', '"{}"'.format(message)], stdout=subprocess.PIPE)
        return process_add_and_commit


    def setup_repo_with_single_commit(self, content="Test" * 100, message="first commit"):
        self._initialize_git_directory().wait()
        self._create_test_file_with_content(content=content)
        self._add_test_file_to_git().wait()
        self._commit_with_message(message=message).wait()


    def get_index_and_packfile_pathes(self):
        filenames = dict()
        pack_directory_path = os.path.join(self.gitDirectoryName,'.git', 'objects', 'pack')
        for filename in os.listdir(pack_directory_path):
            fsplit = filename.split('.')
            if fsplit[-2] in filenames:
                filenames[fsplit[-2]][fsplit[-1]] = os.path.join(pack_directory_path, filename)
            else:
                filenames[fsplit[-2]] = {fsplit[-1]: os.path.join(pack_directory_path, filename)}
        return filenames


    def get_info_from_index(self, path):
        with open(path, 'rb') as fl:
            res = fl.read()
        currByte = 0
        headerBytes = 4
        header = [b for b in res[currByte:(currByte + headerBytes)]]
        currByte += headerBytes

        versionBytes = 4
        version_number = int.from_bytes(res[currByte:(currByte + versionBytes)], byteorder='big')
        currByte += headerBytes

        slot = int(currByte/4)
        fanout_level1_slots = 256
        fanout_level1 = [int.from_bytes(res[4*slot:4*(slot+1)], byteorder='big') for slot in range(slot,(fanout_level1_slots + slot))]
        currByte += fanout_level1_slots * 4

        nrItems = fanout_level1[-1]
        fanout_level2 = [res[currByte + i * 20: currByte + (i+1) * 20].hex() for i in range(nrItems)]
        currByte += 20 * nrItems

        redundcheckBytes = 4
        redundancy_check = [res[currByte + i * redundcheckBytes : currByte + (i+1) * redundcheckBytes] for i in range(nrItems)]
        currByte += redundcheckBytes * nrItems

        bitarrays = [res[(currByte + i * 4): (currByte + (i+1) * 4)] for i in range(nrItems)]
        offsets = [int.from_bytes(b, byteorder='big') if b[0] & 2**7 == 0 else 'bigger than 2GB' for b in bitarrays]
        currByte += 4 * nrItems

        ## NOTE: ONLY IN CASE OF NO FILES LARGER THAN 2GB
        packfile_checksum = res[currByte:(currByte+20)].hex()
        currByte += 20
        indexfile_checksum = res[currByte:(currByte+20)].hex()

        return dict(
            header=header,
            version=version_number,
            cumulative_element_count=fanout_level1,
            object_refs=fanout_level2,
            redundancy_check=redundancy_check,
            offsets=offsets,
            packfile_checksum=packfile_checksum,
            indexfile_checksum=indexfile_checksum
        )




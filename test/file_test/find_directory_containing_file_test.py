from python_utils.file import find_directory_containing_file
import sys

result = find_directory_containing_file(sys.argv[0], "requirements.txt")
print(result)
from fnmatch import fnmatch
import os

# import librsync
#
# s = librsync.signature(file('file1', 'rb'))
#
# with open('delta', 'w') as f:
#     delta = librsync.delta(file('file2', 'rb'), s)
#     f.write(delta.read())

# librsync.patch(file('file1', 'rb'), delta, file('file3', 'wb'))
#
# import tarfile
# with tarfile.open("sample.tar", "w") as tar:
#
#     prev = None
#     for root, dirs, files in os.walk("/home/alex/dev/grandex/lib"):
#         # print root
#         # print dir
#         # print files
#         # root = root[len("/home/alex/dev/grandex/lib") + 1:]
#
#         # for dirname in dirs:
#         #     print os.path.join(root, dirname)
#
#         for filename in files:
#             path_ = os.path.join(root, filename)
#
#             if path_.endswith('.pyc'):
#                 continue
#
#             src = file(path_, 'rb')
#
#
#             print path_
#             signature = librsync.signature(src)
#
#             if prev:
#                 delta = librsync.delta(prev, signature)
#                 print len(delta.read())
#
#             prev = src
#
#             #
#             # break
#
#             # tar.addfile(tar.gettarinfo(arcname=path_, fileobj=delta))
#             # tar.addfile(tar.gettarinfo(arcname=path_, fileobj=signature))
#
#             # print ""
#             # for items in fnmatch.filter(files, "*"):
#             #         print "..." + items
#             # print ""
#
# # tar.close()
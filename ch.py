from time import strftime
import sys
from debian import changelog

with open('debian/changelog') as f:
    dch = changelog.Changelog(f)
    dch.new_block()
    dch.set_author('Alex Rudakov <ribozz@gmail.com>')
    dch.set_date(strftime('%a, %d %b %Y %H:%M:%S %z'))
    dch.set_distributions('trusty')
    dch.set_package('mcloud')
    dch.set_urgency('medium')
    dch.set_version('%s-1' % sys.argv[1])

    dch.add_change('')
    dch.add_change('  * %s' % 'test 123')
    dch.add_change('')

with open('debian/changelog', 'w+') as f:
    dch.write_to_open_file(f)

import glob
import os
import sys
import unittest

from distutils.core import setup, Command

# XXX: importing this here means any external requirements are
# required at RPM build time. Should store canonical version in its
# own file
import bugzilla.base

class TestCommand(Command):
    user_options = [
        ("ro-functional", None,
         "Run readonly functional tests against actual bugzilla instances. "
         "This will be very slow."),
        ("rw-functional", None,
         "Run read/write functional tests against actual bugzilla instances. "
         "As of now this only runs against partner-bugzilla.redhat.com, "
         "which requires an RH bugzilla account with cached cookies. "
         "This will also be very slow.")
    ]

    def initialize_options(self):
        self.ro_functional = False
        self.rw_functional = False

    def finalize_options(self):
        pass

    def run(self):
        os.environ["__BUGZILLA_UNITTEST"] = "1"

        import coverage
        cov = coverage.coverage(omit=["/*/tests/*", "/usr/*"])

        cov.erase()
        cov.start()

        # Reload the library so we get accurate coverage data
        for name in dir(bugzilla):
            attr = getattr(bugzilla, name)
            if type(attr) is type(bugzilla):
                reload(attr)
        reload(bugzilla)

        testfiles = []
        for t in glob.glob(os.path.join(os.getcwd(), 'tests', '*.py')):
            if t.endswith("__init__.py"):
                continue

            base = os.path.basename(t)
            if (base == "ro_functional.py" and not self.ro_functional):
                continue

            if (base == "rw_functional.py" and not self.rw_functional):
                continue

            testfiles.append('.'.join(['tests', os.path.splitext(base)[0]]))


        if hasattr(unittest, "installHandler"):
            try:
                unittest.installHandler()
            except:
                print "installHandler hack failed"

        tests = unittest.TestLoader().loadTestsFromNames(testfiles)
        t = unittest.TextTestRunner(verbosity=1)

        result = t.run(tests)

        cov.stop()
        cov.save()

        err = int(bool(len(result.failures) > 0 or
                       len(result.errors) > 0))
        if not err:
            cov.report(show_missing=False)
        sys.exit(err)


class PylintCommand(Command):
    user_options = []

    def initialize_options(self):
        pass
    def finalize_options(self):
        pass

    def run(self):
        os.system("pylint "
            "--reports=n "
            "--output-format=colorized "
            "--dummy-variables-rgx=\"dummy|ignore*|.*ignore\" "
            # Lines in modules, function size, ...
            "--disable Design "
            # Line length, spacing, ...
            "--disable Format "
            # Duplicate code
            "--disable Similarities "
            # Use of * or **
            "--disable W0142 "
            # Name doesn't match some style regex
            "--disable C0103 "
            # FIXME comments
            "--disable W0511 "
            # C0111: No docstring
            "--disable C0111 "
            # W0603: Using the global statement
            "--disable W0603 "
            "bin/bugzilla tests/")


setup(name='python-bugzilla',
      version=str(bugzilla.base.version),
      description='Bugzilla XMLRPC access module',
      author='Will Woods',
      author_email='wwoods@redhat.com',
      url='https://fedorahosted.org/python-bugzilla/',
      packages = ['bugzilla'],
      scripts=['bin/bugzilla'],
      data_files=[('share/man/man1', ['bugzilla.1'])],

      cmdclass={
        "test" : TestCommand,
        "pylint" : PylintCommand,
      }
)

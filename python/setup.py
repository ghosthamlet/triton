import os
import re
import sys
import sysconfig
import platform
import subprocess
import distutils
import glob
from distutils.version import LooseVersion
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.test import test as TestCommand
import distutils.spawn


def find_llvm():
    versions = ['9.0', '9', '90', '8.0', '8', '80']
    supported = ['llvm-config-{v}'.format(v=v) for v in versions]
    paths = [distutils.spawn.find_executable(cfg) for cfg in supported]
    paths = [p for p in paths if p is not None]
    if paths:
      return paths[0]
    config = distutils.spawn.find_executable('llvm-config')
    instructions = 'Please install llvm-{8, 9, 10}-dev'
    if config is None:
        raise RuntimeError('Could not find llvm-config. ' + instructions)
    version = os.popen('{config} --version'.format(config=config)).read()
    raise RuntimeError('Version {v} not supported. '.format(v=version) + instructions)


class CMakeExtension(Extension):
    def __init__(self, name, path, sourcedir=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)
        self.path = path


class CMakeBuild(build_ext):

    def run(self):
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError("CMake must be installed to build the following extensions: " +
                               ", ".join(e.name for e in self.extensions))

        if platform.system() == "Windows":
            cmake_version = LooseVersion(re.search(r'version\s*([\d.]+)', out.decode()).group(1))
            if cmake_version < '3.1.0':
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        self.debug = True
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.path)))
        # python directories
        python_include_dirs = distutils.sysconfig.get_python_inc()
        python_lib_dirs = distutils.sysconfig.get_config_var('LIBDIR')
        cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                      '-DBUILD_TESTS=OFF',
                      '-DBUILD_PYTHON_MODULE=ON',
                      '-DPYTHON_INCLUDE_DIRS=' + python_include_dirs,
                      '-DLLVM_CONFIG=' + find_llvm()]
        # tensorflow compatibility
        try:
            import tensorflow as tf
            tf_abi = tf.__cxx11_abi_flag__ if "__cxx11_abi_flag__" in tf.__dict__ else 0
            tf_include_dirs = tf.sysconfig.get_include()
            tf_libs = tf.sysconfig.get_link_flags()[1].replace('-l', '')
            cmake_args += ['-DTF_INCLUDE_DIRS=' + tf_include_dirs,
                        '-DTF_LIB_DIRS='     + tf.sysconfig.get_lib(),
                        '-DTF_LIBS='         + tf_libs,
                        '-DTF_ABI='          + str(tf_abi)]
        except ModuleNotFoundError:
            pass

        cfg = 'Debug' if self.debug else 'Release'
        cfg = 'Release'
        build_args = ['--config', cfg]

        if platform.system() == "Windows":
            cmake_args += ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(cfg.upper(), extdir)]
            if sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']
            build_args += ['--', '/m']
        else:
            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j4']

        env = os.environ.copy()
        env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(env.get('CXXFLAGS', ''),
                                                              self.distribution.get_version())
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        sourcedir =  os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        subprocess.check_call(['cmake', sourcedir] + cmake_args, cwd=self.build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=self.build_temp)
       

find_llvm()

directories = [x[0] for x in os.walk(os.path.join(os.path.pardir, 'include'))]
data = []
for d in directories:
    files = glob.glob(os.path.join(d, '*.h'), recursive=False)
    data += [os.path.relpath(f, os.path.pardir) for f in files]

setup(
    name='triton',
    version='0.1',
    author='Philippe Tillet',
    author_email='ptillet@g.harvard.edu',
    description='A language and compiler for custom Deep Learning operations',
    long_description='',
    packages=['triton', 'triton/_C', 'triton/ops'],
    package_data={'': data},
    ext_modules=[CMakeExtension('triton', 'triton/_C/')],
    cmdclass=dict(build_ext=CMakeBuild),
    zip_safe=False,
)

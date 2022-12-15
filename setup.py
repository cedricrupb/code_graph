from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
  name = 'code_graph',
  packages = ['code_graph'], 
  version = '0.0.1', 
  license='MIT',     
  description = 'Fast program graph generation in Python',
  long_description = long_description,
  long_description_content_type="text/markdown",
  author = 'Cedric Richter',                   
  author_email = 'cedricr.upb@gmail.com',    
  url = 'https://github.com/cedricrupb/code_graph',  
  download_url = '', 
  keywords = ['code', 'graph', 'program', 'language processing'], 
  install_requires=[          
          'tree_sitter',
          'GitPython',
          'requests',
          'code_ast'
      ],
  classifiers=[
    'Development Status :: 3 - Alpha',    
    'Intended Audience :: Developers',  
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3', 
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
  ],
)
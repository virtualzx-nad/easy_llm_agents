from setuptools import setup, find_packages

setup(
    name='lm_agents',
    version='0.0.1',
    description='Easily enhance language model agents',
    author='Xiaolei Zhu',
    author_email='virtualzx@gmail.com',
    url='git@github.com:virtualzx-nad/easier_llm_agents.git',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)

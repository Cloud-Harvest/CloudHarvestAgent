from setuptools import setup, find_packages

# load the metadata from the meta.json file
with open('meta.json') as meta_file_stream:
    from json import load
    meta = load(meta_file_stream)

# load requirements from requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

config = dict(packages=find_packages(include=['CloudHarvestCoreTasks*']),
              install_requires=required)

config = config | meta


def main():
    setup(**config)


if __name__ == '__main__':
    main()

#!/bin/env python3
from yaml import load, FullLoader
from os.path import abspath, expanduser, exists, join

for directory in ('/src/app', './app', '../app'):
    if exists(directory):
        break

if directory:
    directory = abspath(expanduser(directory))
    print(f'Found app directory at {directory}')

else:
    raise FileNotFoundError('No app directory found')

# Get the configuration
with open(join(directory, 'harvest.yaml')) as configuration_file:
    configuration = load(configuration_file, Loader=FullLoader)

# The plugins.txt file is a requirements.txt file that contains the URLs of the plugins to install
with open(join(directory, 'plugins.txt'), 'w') as plugins_file:
    for plugin in configuration.get('plugins') or []:

        # Check if the plugin is a git repository or a URL
        from re import compile

        git_pattern = compile(r'^(git\+|(http|https)://)')
        if git_pattern.match(plugin['url_or_package_name']):
            # Get the package name from the URL
            package_name = plugin['url_or_package_name'].split('/')[-1].split('.')[0]
            branch_name = plugin.get('branch') or 'master'
            output_string = f'{package_name} @ {plugin["url_or_package_name"]}@{branch_name}\n'

        else:
            output_string = plugin['url_or_package_name']

        plugins_file.write(output_string)

print(f'Plugins written to {join(directory, "plugins.txt")}')

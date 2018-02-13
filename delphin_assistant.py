import sublime
import sublime_plugin
import re
import os
import shutil
from .scripts.make_item import main as make

delphin_folder = None
package_settings = 'delphin_assistant.sublime-settings'


def load_path():
    global delphin_folder
    delphin_folder = sublime.packages_path() + '/User/delphin-assistant/'


def is_testsuite(file_name):
    if file_name is not None:
        tokens = file_name.split('.')
        if tokens[len(tokens) - 1] == 'tsdb':
            return True
    return False


class TsdbEventListener(sublime_plugin.EventListener):
    """
    Watches Sublime events to regenerate the line syntax when needed
    """
    def on_activated(self, view):
        self.generate_line_syntax(view)

    def on_post_save(self, view):
        self.generate_line_syntax(view)

    def generate_line_syntax(self, view):
        """
        Regenerates the line syntax if the current file is an [incr tsdb()] testsuite
        """
        if is_testsuite(view.file_name()):
            view.run_command('compile_tsdb_syntax')


class BaseTsdbTestsuiteCommand(sublime_plugin.TextCommand):
    def retrieve_folder(self):
        """
        Retrieves the last folder that was used when compiling the current file

        :return: The name of the folder cached, or an empty string if there is no cached folder
        """
        file_name = self.view.file_name()
        folder_map = self.settings.get('tsdb_folder_map', {})
        return folder_map[file_name] if file_name in folder_map else ''

    def cache_folder(self, folder_name):
        """
        Caches a folder name along with the current file name for later use

        :param folder_name: The name of folder to cache with the current file name
        """
        folder_map = self.settings.get('tsdb_folder_map', {})
        folder_map[self.view.file_name()] = folder_name
        self.settings.set('tsdb_folder_map', folder_map)

    def get_skeleton_path(self):
        """
        Retrieves the path to the TSDB skeleton directory

        :return: The path to the TSDB skeleton directory, or the path to the directory the current file is contained in
                 if the skeleton directory is not set
        """
        skeleton_path = self.settings.get('tsdb_skeleton_dir')

        if not skeleton_path or skeleton_path == '':
            testsuite_path = self.view.file_name()
            skeleton_path = '/'.join(testsuite_path.split('/')[:-1])

        if not skeleton_path[-1] == '/':
            skeleton_path += '/'

        return skeleton_path


class CompileTsdbTestsuiteCommand(BaseTsdbTestsuiteCommand):
    def run(self, edit):
        """
        Prompts the user for a folder to store a compiled testsuite
        """
        if is_testsuite(self.view.file_name()):
            self.settings = sublime.load_settings(package_settings)
            folder_name = self.retrieve_folder()
            self.view.window().show_input_panel("Enter a directory", folder_name, self.compile, None, None)
        else:
            print('This is not a [incr tsdb()] testsuite!')

    def compile(self, folder_name):
        """
        Compiles the current view into an item file
        Creates the environment if necessary and possible

        :param folder_name: The name of the folder to store the item file in
        """
        self.cache_folder(folder_name)

        mappings = self.get_mappings()
        verb = ''
        testsuite_path = self.view.file_name()
        skeleton_path = self.get_skeleton_path()
        item_path = skeleton_path + folder_name + '/item'

        self.make_environment(skeleton_path, folder_name)

        make(testsuite_path, item_path, verb, mappings)

    def get_mappings(self):
        """
        Retrieves the compilation mappings

        :return: An array of 2-tuples
        """
        return [(mapping['from'], mapping['to']) for mapping in self.settings.get('tsdb_make_map')]

    def make_environment(self, skeleton_path, folder_name):
        """
        Establishes the environment for a compiled testsuite if it does not exist already
        If a Relations file is found, it is copied into the new directory, and if an Index.lisp file is found, it is
        edited to include the new test.

        :param skeleton_path: The path to the skeleton directory
        :param folder_name: The name of the new folder
        """
        if not os.path.exists(skeleton_path + folder_name):
            os.makedirs(skeleton_path + folder_name)

            if os.path.exists(skeleton_path + 'Relations'):
                shutil.copyfile(skeleton_path + 'Relations', skeleton_path + folder_name + '/relations')

            if os.path.exists(skeleton_path + 'Index.lisp'):
                lines = None
                new_line = '((:path . "{}") (:content . "Test suite collected for {}."))\n'.format(folder_name, folder_name)
                with open(skeleton_path + 'Index.lisp') as index_file:
                    lines = index_file.readlines()
                    lines.insert(-1, new_line)

                with open(skeleton_path + 'Index.lisp', 'w') as index_file:
                    index_file.write(''.join(lines))


class RemoveTsdbTestsuiteCommand(BaseTsdbTestsuiteCommand):
    def run(self, edit):
        self.settings = sublime.load_settings(package_settings)
        folder_name = self.retrieve_folder()
        self.view.window().show_input_panel('Which testsuite should be removed?', folder_name, self.remove, None, None)

    def remove(self, folder_name):
        """
        Removes the environment for a compiled TSDB testsuite

        :param folder_name: The name of the folder the testsuite is stored in
        """
        skeleton_path = self.get_skeleton_path()

        if folder_name != '':
            if os.path.exists(skeleton_path + folder_name):
                shutil.rmtree(skeleton_path + folder_name)
            if os.path.exists(skeleton_path + 'Index.lisp'):
                lines = None
                with open(skeleton_path + 'Index.lisp') as index_file:
                    lines = index_file.readlines()

                for i in reversed(range(len(lines))):
                    if 'Test suite collected for ' + folder_name in lines[i]:
                        del lines[i]

                with open(skeleton_path + 'Index.lisp', 'w') as index_file:
                    index_file.write(''.join(lines))
        elif os.path.exists(skeleton_path + 'item'):
            os.remove(skeleton_path + 'item')


class CompileTsdbSyntaxCommand(sublime_plugin.TextCommand):
    """
    Reads the current file and the package-specific settings to generate a custom line syntax highlight
    """
    def run(self, edit):
        if delphin_folder is None:
            load_path()

        # Ensure that a delphin-assistant directory exists in the User directory
        if not os.path.isdir(delphin_folder):
            os.mkdir(delphin_folder)

        settings = sublime.load_settings(package_settings)
        cache = settings.get('tsdb_cache')
        word_segmented_lines = settings.get('tsdb_tokenized_lines')
        line_names = self.get_line_names()
        split_chars = settings.get('tsdb_split')
        split_chars = re.escape(split_chars)

        new_settings = [word_segmented_lines, line_names, split_chars]
        if not cache == new_settings:
            lines = self.generate_line_syntax(line_names, word_segmented_lines, split_chars)
            self.write_syntax(lines)
            self.write_snippet(line_names)
            settings.set('tsdb_cache', new_settings)

    def get_line_names(self):
        """
        Retrieves the names of the line from the current document
        """
        region = self.view.find('^Lines:.*', 0)
        section = self.view.substr(region)
        tokens = section.split(':')
        line_names = ['main']  # Set a default line, just in case the user hasn't added a Lines: field

        if len(tokens) == 2:
            line_names = tokens[1].strip().split()
        return line_names

    def generate_line_syntax(self, names, word_segmented, split_chars):
        """
        Generates the sublime-syntax needed to properly highlight the current file

        :param names: A list of names of the lines
        :param word_segmented: A list containing the names of the lines that need to be highlighted per word
        :param split_chars: A regular expression escaped string of special characters to split words on
        :return: A list, where each element is a line that needs to be written to the syntax file
        """
        lines = []
        length = len(names)

        for i in range(length):
            # The first line needs to be called "main" for sublime to pick up on it
            if i == 0:
                lines.append('  main:')
            else:
                lines.append('  ' + names[i] + '-line:')

            # All lines can be commented out
            lines.append('    - include: comment')

            # Word-segmented lines and normal lines need to be highlighted differently
            if names[i] in word_segmented:
                lines.append('    - match: \'[^\\s' + split_chars + ']+\'')
                lines.append('      scope: variable.parameter')

                if i == length - 1:
                    lines.append('      pop: true')
                else:
                    lines.append('      set: [' + names[i + 1] + '-line, word2]')
            else:
                lines.append('    - match: \'\\S+(\\s+\\S+)*\'')
                lines.append('      scope: string.quoted.double.tsdb')

                if i == length - 1:
                    lines.append('      pop: true')
                else:
                    lines.append('      set: ' + names[i + 1] + '-line')
            lines.append('')

        return lines

    def write_syntax(self, lines):
        template = sublime.load_resource('Packages/delphin-assistant/templates/tsdb-lines.txt')

        with open(delphin_folder + 'tsdb-lines.sublime-syntax', 'w') as line_syntax:
            line_syntax.write(template)
            line_syntax.write('\n'.join(lines))

    def write_snippet(self, line_names):
        lines = ['${' + str(i + 6) + ':<' + name + ' line>}' for i, name in enumerate(line_names)]
        template = sublime.load_resource('Packages/delphin-assistant/templates/tsdb-test.txt')
        template = re.sub('!!!', '\n'.join(lines), template)

        with open(delphin_folder + 'tsdb-test.sublime-snippet', 'w') as snippet:
            snippet.write(template)

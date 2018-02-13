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


class CompileTsdbTestsuiteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if is_testsuite(self.view.file_name()):
            settings = sublime.load_settings(package_settings)
            folder_name = settings.get('tsdb_last_folder', '')
            self.view.window().show_input_panel("Enter a directory", folder_name, self.compile, None, None)
        else:
            print('This is not a [incr tsdb()] testsuite!')

    def compile(self, folder_name):
        settings = sublime.load_settings(package_settings)
        settings.set('tsdb_last_folder', folder_name)
        skeleton_dir = settings.get('tsdb_skeleton_dir')
        mappings = [(mapping['from'], mapping['to']) for mapping in settings.get('tsdb_make_map')]
        testsuite_path = self.view.file_name()
        verb = ''

        if not skeleton_dir or skeleton_dir == '':
            skeleton_dir = '/'.join(testsuite_path.split('/')[:-1])

        if not skeleton_dir[-1] == '/':
            skeleton_dir += '/'

        item_path = skeleton_dir + folder_name + '/item'
        self.make_environment(skeleton_dir, folder_name)

        make(testsuite_path, item_path, verb, mappings)

    def make_environment(self, skeleton_path, folder_name):
        if not os.path.exists(skeleton_path + folder_name):
            os.makedirs(skeleton_path + folder_name)

            if os.path.exists(skeleton_path + 'Relations'):
                shutil.copyfile(skeleton_path + 'Relations', skeleton_path + folder_name + '/relations')

            if os.path.exists(skeleton_path + 'Index.lisp'):
                lines = None
                with open(skeleton_path + 'Index.lisp') as index_file:
                    lines = index_file.readlines()
                    lines.insert(-1, '((:path . "{}") (:content . "Test suite collected for {}."))'.format(folder_name, folder_name))

                with open(skeleton_path + 'Index.lisp', 'w') as index_file:
                    index_file.write('\n'.join(lines))


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

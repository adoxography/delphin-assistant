import sublime
import sublime_plugin
import re
import shutil

syntax_template = None
snippet_template = None
syntax_file = None
snippet_file = None

def load_paths():
    global syntax_template, snippet_template, syntax_file, snippet_file
    pwd = sublime.packages_path() + '/lkb-assistant/'
    syntax_template = pwd + 'templates/tsdb-lines.txt'
    snippet_template = pwd + 'templates/tsdb-test.txt'
    syntax_file = pwd + 'tsdb-lines.sublime-syntax'
    snippet_file = pwd + 'tsdb-test.sublime-snippet'
    


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
        file_name = view.file_name()
        if file_name is not None:
            tokens = file_name.split('.')
            if tokens[len(tokens) - 1] == 'tsdb':
                view.run_command('compile_tsdb_syntax')


class CompileTsdbSyntaxCommand(sublime_plugin.TextCommand):
    """
    Reads the current file and the package-specific settings to generate a custom line syntax highlight
    """
    def run(self, edit):
        if syntax_template is None:
            load_paths()

        settings = sublime.load_settings('lkb_assistant.sublime-settings')
        cache = settings.get('tsdb_cache')
        word_segmented_lines = settings.get('tsdb_tokenized_lines')
        line_names = self.get_line_names()
        split_chars = settings.get('tsdb_split')
        split_chars = re.escape(split_chars)

        x = [word_segmented_lines, line_names, split_chars]
        if not cache == x:
            lines = self.generate_line_syntax(line_names, word_segmented_lines, split_chars)
            self.write_syntax(lines)
            self.write_snippet(line_names)
            settings.set('tsdb_cache', x)


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
        shutil.copyfile(syntax_template, syntax_file)

        line_syntax = open(syntax_file, 'a')
        line_syntax.write('\n'.join(lines))
        line_syntax.close()

    def write_snippet(self, line_names):
        lines = ['${' + str(i + 6) + ':<' + name + ' line>}' for i, name in enumerate(line_names)]

        template = open(snippet_template)
        data = ''.join(template.readlines())
        template.close()

        data = re.sub('!!!', '\n'.join(lines), data)

        snippet = open(snippet_file, 'w')
        snippet.write(data)
        snippet.close()

# LKB Assistant
This package lets [Sublime Text 3](https://www.sublimetext.com/) handle file types associated with the Linguistic Knowledge Builder ([LKB](http://moin.delph-in.net/LkbTop)) elegantly.

## Features
* Syntax highlighting for TDL and [incr tsdb()] testsuites
* Commenting shortcut with `CTRL+/`
* [incr tsdb()] test snippet

## Usage
At present, cloning the repository into Sublime's Packages directory will enable the plugin. After installation, all features are available in files with the extensions .tdl and .tsdb for TDL and [incr tsdb()] testsuites, respectively.

### [incr tsdb()] syntax
All [incr tsdb()] tests are expected to begin with the following four lines, in order:
* Source
* Vetted
* Judgment
* Phenomena

To ensure that these lines are created in the correct order, the package comes with a `test` snippet which will generate the shell of a test for you: just type "test" and press `TAB` while in a .tsdb file.

Subsequent lines are open to user customization. The LKB Assistant reads from the first line it finds in the testsuite that begins with `Lines:` to determine the number of lines that should follow the four lines mentioned earlier. By default, it will highlight any line labelled orth-seg or gloss by token, such that odd-numbered tokens are a different colour than even-numbered tokens. To adjust which lines should be token-separated, browse to `Preferences -> Package Settings -> LKB Assistant -> Settings` and in your user settings, create a key/value pair for `"tsdb_tokenized_lines"`. Note that the value must be an array.

By default, tokens will be separated by whitespace and the following characters: ``!#$%&()*+,-./:;<=>?@[]^_\`{|}~\\``. These characters can be changed by adjusting the `"tsdb_split"` value in your LKB Assistant user preferences. Note that splitting on the single quote (`'`) is not supported at this time.

## To do
* Add an internal sublime command for compiling testsuites

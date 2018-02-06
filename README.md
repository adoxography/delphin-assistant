# LKB Assistant
This package lets [Sublime Text 3](https://www.sublimetext.com/) handle file types associated with the Linguistic Knowledge Builder ([LKB](http://moin.delph-in.net/LkbTop)).

## Features
* Syntax highlighting for TDL and [incr tsdb()] testsuites
* Commenting shortcut with `CTRL+/`
* [incr tsdb()] test snippet: type "test" and press `TAB` for a base [incr tsdb()] test

## Usage
At present, cloning the repository into Sublime's Packages directory will enable the plugin. After installation, all features are available in files with the extensions .tdl and .tsdb for TDL and [incr tsdb()] testsuites, respectively.

## Limitations
The [incr tsdb()] testsuite syntax is expecting test lines in a specific order:
* Source
* Vetted
* Judgment
* Phenomena
* orth
* orth-seg
* gloss
* translat

If this ordering is not used, the syntax will display it as an error. Using the included `test` snippet will ensure that all fields are present and in order.

## To do
* Allow the user to customize which lines appear in their testsuite, and in which order
* Add an internal sublime command for compiling testsuites

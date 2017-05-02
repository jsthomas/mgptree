################################################################################
# MGPTree Version 2.0 --- May 2, 2014
# Copyright 2014 Joseph Thomas (jthomas@math.arizona.edu)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#######################################################################
#
# Program Description: This python script extracts data from the
# Mathematics Genealogy Project's (MGP) website and provides a way of
# visualizing this data.
#
# For an extensive example of how to use this program, please see:
#
# http://math.arizona.edu/~jthomas/math-genealogy-visualizer.html
#
# Here is a typical use-case:
#
# 1) A user wishes to visualize the genealogy of a particular
# collection of mathematicians, so he writes their names down in the
# file "names.txt".
#
# 2) The user gives names.txt to mgptree as input and uses the "find
# IDs" option to search for the MGP IDs that correspond to those
# names. The script records this data in a file.
#
# 3) In the event some of the names are not found, the user can fill
# in the remaining ID data by hand.
#
# 3) The user gives the ID data to mgptree as input, along with a
# number that specifies the number indicating how many generations
# back the program should search.
#
# 4) mgptree produces a database as output. (This step takes time.)
#
# 5) Now, using the database, the user can rapidly produce various
# visualizations of the data.
#
# Since the options to the program are handled by optparse, I will not
# document them here.
################################################################################

import optparse
import re, sys, pickle, textwrap
import requests

GRAPH_FORMAT_STRING = "digraph G{\n node[width = 0.5 fontname=Courier shape=rectangle]\n %s }"

DEBUG = False

def build_opt_parser():
    p = optparse.OptionParser()
    p.add_option('--verbose', '-v', dest="verbose_on", action="store_true",
                 default=False, help="Print progress data to stderr.")

    p.add_option('--scrape', '-s', dest="scrape_on", action="store_true",
                 default=False, help="Recover data from the MGP.")
    p.add_option('--plot', '-p',  dest="graph_on", action="store_true",
                 default=False, help="Use graphviz to draw a geneaology.")
    p.add_option('--generations', '-g',  dest="gen_depth", default=3,
                 help="Determines how many generations into the past to search/print.")

    p.add_option('--input', '-i', dest="input_file", default=None)
    p.add_option('--output', '-o', dest="output_file", default=None)
    return p

def main():
    print "In main"
    parser = build_opt_parser()
    global options
    options, arguments = parser.parse_args()
    Node.verbose_on = options.verbose_on

    if options.verbose_on:
        sys.stdout.write("Verbose option is on. Printing progress.\n")

    operation_list = [ options.scrape_on, options.graph_on ]
    true_count = operation_list.count( True )

    if options.scrape_on:
        names = validate_scrape( parser, options )
        nodes = scrape( names, int(options.gen_depth) )
        pickle_graph_ds( nodes, options.output_file )

    elif options.graph_on:
        nodes = validate_graph( parser, options )
        nodes_txt = graph( nodes, int(options.gen_depth) )
        write_graph_text( nodes_txt, options.output_file )

    else:
        sys.stderr.write("Error: You must select either -s or -p.\n")
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


################################################################################
# Procedure: validate_scrape
#
# Input: Parser and options objects from optparse
#
# Output: A list of well-formed name tuples.
#
# Effects: Checks the options object to confirm the inputs are well formed.
#
################################################################################

def validate_scrape( parser, options ):
    if options.input_file is None:
        sys.stderr.write("You must provide as input a file of names "
                         + "you wish to search for in the MGP.\n")
        parser.print_help()
        sys.exit(1)
    try:
        namefile = open( options.input_file )
    except IOError:
        sys.stderr.write("Error: Input file %s does not exist.\n" % options.names_file )
        parser.print_help()
        sys.exit(1)

    text = namefile.read().decode('utf8')
    names = [ parseName(line) for line in text.split('\n') if len( line ) > 0 ]
    namefile.close()

    return names

################################################################################
# Procedure: parseName
#
# Input: A string consisting of a person's names, in the form "last,
# first middle" (where the middle name is optional).
#
# Output: A tuple of those same names, this time in the form (last,
# first, middle) where each name has been stripped of whitespace and
# set to lowercase. If the middle name does not exist, it will be
# listed as an empty string.
#
################################################################################

def parseName( namestring ):

    if ',' in namestring:
        kk = namestring.index(',')
        last = (namestring[0:kk]).strip().lower()
        namestring = (namestring[kk:]).replace(',','')
        names = [ last ] + [ name.strip().lower() for name in namestring.split() ]

    else:
        namestring = namestring.replace(',','')
        names = [ name.strip().lower() for name in namestring.split() ]

    if len( names ) == 2:
        return ( names[0], names[1], "" )
    if len( names ) >= 3:
        return ( names[0], names[1], names[2] )
    else:
        sys.stderr.write( ("Error: Only detected a single name in string %s. " +
                           "Please provide a first and last name.\n") % namestring )
        sys.exit(1)

################################################################################
# Procedure: scrape
#
# Input: A list of names to search for and an integer number of
# generations to search back.
#
# Output: A dictionary object mapping MGP IDs to Node objects.
#
################################################################################

def scrape( names, gens ):
    node_dict = {}
    pairs = [ ( name, fetchIDNum(*name) ) for name in names ]
    pairs = filter( lambda pair : pair[1] > 0, pairs )
    for pair in pairs:
        Node( pair[1], 0, gens, node_dict )

    return node_dict

################################################################################
# Procedure: pickle_graph_ds
#
# Input: A collection of MGP nodes.
#
# Effect: Writes the nodes to a file and prints a message recording this.
#
################################################################################

def pickle_graph_ds( nodes, filename ):
    if filename is None:
        filename = "database.mgp"
    pickle.dump( nodes, open( filename, 'wb') )
    sys.stdout.write( 'Saved %d records to file %s.\n' \
                          % ( len(nodes), filename ) )


################################################################################
# Procedure: validate_graph
#
# Input: Parser and options objects from optparse.
#
# Effects: Checks user input when in plotting mode, aborts if the
# input is not well formed.
#
# Output: An un-pickled graph data structure.
#
################################################################################

def validate_graph( parser, options ):
    if options.input_file == None:
        sys.stderr.write("Error: You must provide a saved database as input.\n")
        parser.print_help()
        sys.exit(1)

    try:
        nodes = pickle.load( open( options.input_file, 'rb' ) )
    except:
        sys.stderr.write("Error: Could not read file %s.\n" % options.input_file )
        parser.print_help()
        sys.exit(1)

    return nodes

################################################################################
# Procedure: graph
#
# Input: A graph data structure (nodes) and a generation number. Nodes
# whose generation number is greater than the input generation number
# will not be displayed.
#
# Output: A string representation of the graph.
#
################################################################################

def graph( nodes, gen_depth ):
    node_string = ""
    for (key,node) in nodes.items():
        if node.gen <= gen_depth:
            node_string += node.dot_string( node.gen != gen_depth )
    return node_string

################################################################################
# Procedure: graph
#
# Input: A string containing a textual representation of the nodes in
# the graph, and a filename.
#
# Effect: A textual representation of the graph is written to stdout
# or the disk (to a file with the input filename).
#
################################################################################

def write_graph_text( node_text, filename ):

    fulltext = GRAPH_FORMAT_STRING % node_text
    if filename is None:
        sys.stdout.write( fulltext )
    else:
        outfile = open(filename, 'w')
        outfile.write( fulltext.encode('utf8') )
        outfile.close()

################################################################################
# Procedure: sameName
#
# Input: A pair of names, which are tuples of the form (last, first, middle).
#
# Output: A boolean, indicating whether the names agree.
#
# Caveats: Currently, middle names are not checked.
#
################################################################################

def sameName( name1, name2 ):
    last1 = name1[0].lower()
    last2 = name2[0].lower()
    first1 = name1[1].lower()
    first2 = name2[1].lower()
    return last1 == last2 and first1 == first2

################################################################################
# Procedure: fetchIDNum
#
# Input: Last, first, and middle names (strings) for a given person.
#
# Output: An integer that is -1 if the name was not found on the MGP
# (or the search returned multiple hits), or the ID number assigned by
# the MGP otherwise.
#
################################################################################

def fetchIDNum( last, first, middle ):
    if options.verbose_on:
        sys.stdout.write("Searching MGP for %s, %s, %s.\n" % ( last, first, middle))

    url = 'http://genealogy.math.ndsu.nodak.edu/query-prep.php'
    values = {'given_name' : '%s' % first, 'family_name' : '%s' %last,
              'other_names' : middle }

    print values

    text = (requests.post(url,values)).text

    pairs = [ (int(pair[0]), parseName( pair[1] ) ) for
              pair in re.findall( u'<tr><td><a href="id.php\?id=(\d+)">(.+)</a></td>', text ) ]
    pairs = filter( lambda pair :  sameName( pair[1], (last,first,middle) ), pairs )

    if len(pairs) == 0:
        sys.stderr.write("Unable to find a record for %s, %s %s\n" % ( last, first, middle ) )
        return -1
    if len(pairs) > 1:
        sys.stderr.write("Found multiple records for %s, %s %s\n" % ( last, first, middle ) )
        return -1
    else:
        if options.verbose_on:
            sys.stdout.write( "Found --- ID: %d \n" % ( pairs[0][0] ) )
        return pairs[0][0]

#############################################################################
#
#  Class Node
#
#  Each instance of the Node class is responsible for recording all of
#  the data that has been collected about a particular
#  mathematician. Typically this information comes from entries in the
#  Mathematics Genealogy project, and thus will not be complete.
#
#  The most important piece of data the Node class manages is the
#  (unique) ID number assigned to each mathematician by the
#  MGP. This integer provides the best way
#  to search for a given mathematician, since mapping names to people
#  can be quite difficult.
#
#############################################################################

class Node:
    verbose_on = False

    def __init__( self, id_number, gen, max_gen, node_dict ):
        node_dict[ id_number ] = self;
        self.id_num = id_number
        self.gen = gen

        url = "http://genealogy.math.ndsu.nodak.edu/id.php?id=%d" % id_number
        text = requests.post(url).text

        self.extractPersonalData( text )
        if Node.verbose_on :
            sys.stdout.write( "Recovered record: %s %s %s %s\n" %
                              (self.name, self.title, self.institution, self.year_of_doctorate ) )

        if gen >= max_gen : return

        txt_start = text.find( "Advisor" )
        if txt_start == -1:
            sys.stderr.write("Error finding advisor for %s\n" % (self.name))
            return
        txt_stop = text.find( "Student" )

        adv_text = text[ txt_start : txt_stop ]

        advs = [int( id_string )
                for id_string in re.findall('id.php\?id=(\d+)', adv_text)]

        for adv in advs:
            if adv in node_dict:
                self.advised_by( node_dict[ adv ] )
            else:
                advisor = Node( adv, gen + 1, max_gen, node_dict )
                self.advised_by( advisor )

    def extractPersonalData( self, text ):
        self.year_of_doctorate = ""
        self.institution = ""
        self.nationality = ""
        self.advisors = []

        results = re.findall( "<title>The Mathematics Genealogy Project - (.+)</title>", text)
        if len( results ) > 0:
            self.name = results[0]

        results = re.findall( '<span style="margin-right: 0.5em">(.+)<span style=', text)
        if len( results ) > 0:
            self.title = results[0]

        results = re.findall('margin-left: 0.5em">(.+)</span>(.+)</span>', text)
        if len( results ) > 0:
            self.institution, self.year_of_doctorate = results[0]

    def advised_by( self, other_node ):
        self.advisors.append( other_node )

    def dot_string( self, print_advs, brief=True ):
        node_str = ""
        if brief:
            name = textwrap.fill(self.name,20).replace('\n', '\\n')
            node_str = "node%d[label=\"%s\\n%s\"];\n" % (self.id_num, self.name, self.year_of_doctorate)
        else:
            institute = textwrap.fill(self.institution,25).replace('\n','\\n')
            node_str = "node%d[label=\"%s\\n%s\\n%s\"];\n" % (self.id_num, self.name, institute, self.year_of_doctorate)
        if print_advs:
            for adv in self.advisors:
                node_str += "node%d->node%d;\n" % (adv.id_num, self.id_num);

        return node_str

#############################################################################
# End of Class Node
#############################################################################

#############################################################################
# This piece of the code is responsible for making this file behave
# like a script. It says that when we call up the program from the
# command line, the "main" procedure is the first procedure that
# should be run.
#############################################################################
if __name__ == '__main__':
    main()

import sys
import csv      #to read in the csv file
import hashlib  #needed to produce shorter contributor node names

'''
campaign_finance.py

script to produce a graphviz dot file suitable for passing into neato, using a
CSV as input.  Only really a prototype for showing it is possible...

Author:  John Jensen, 2009.  
License: Public Domain.

Sample CSV file:
"First name","Last Name","Position","Contributor","Amount","Class"
"Bob","Fearnley","Councillor","Self","$1,563.57",0
"Bob","Fearnley","Councillor","Pinnacle International","$1,000.00",2
"Bob","Fearnley","Councillor","DMRC Properties",$500.00,2
"Bob","Fearnley","Councillor","Jonathan Baker",$400.00,1
"Bob","Fearnley","Councillor","Rusty Gull",$275.00,2
"Bob","Fearnley","Councillor","Moyna Fearnley",$200.00,1

Usage:

python finance_graph.py contributions.csv > graph.dot && neato -Tpng -o graph.png graph.dot

'''


def clean(n):
    ''' cleans up a dollar amount by removing commas and dollar signs'''
    return float(n.replace('$','').replace(',',''))

class Contribution:
    def __init__(self, candidate, contributor, amount):
        self.contributor = contributor
        self.candidate = candidate
        self.amount = amount
        
class Candidate:
    def __init__(self, name):
        self.name = name
    def nodename(self):
        return self.name.replace(' ','')
    def __eq__(self, other):
        return self.name == other.name
    def __hash__(self):
        return id(self.name)
        
class Contributor:
    def __init__(self, name, klass):
        self.name = name
        self.klass = klass
    def nodename(self):
        return self.name.replace(' ','').replace("'","")
    def nodename_short(self):
	''' A shorter name to use for the node, based on the MD5 of the nodename.  Used for individuals'''
        return 'h' + hashlib.md5(self.nodename()).hexdigest()[:4]
    def __eq__(self, other):
        return self.name == other.name
    def __hash__(self):
        return id(self.name)
        
class Contributions:
    def __init__(self):
        self.contributions = []
        self.candidates = []
        self.contributors = []

    def add(self, c):
        self.contributions.append(c)
        
        if not c.candidate in self.candidates:
            self.candidates.append(c.candidate)
        if not c.contributor in self.contributors:
            self.contributors.append(c.contributor)
        
    
    #candidates   
    def total_for_candidate(self, candidate, ignoreself=False):
        return sum([c.amount * (ignoreself + c.klass !=1) for c in self.candidates[candidate]])

    def max_for_candidate(self, candidate, ignoreself=False):
        return max([c.amount * (ignoreself + c.contributor.klass !=1) for c in self.contributions if c.candidate == candidate])
        
    def max_for_all_candidates(self, ignoreself=False):
        return max([c.amount * (ignoreself + c.contributor.klass !=1) for c in self.contributions])

    def normalized_total_for_candidate(self, candidate, ignoreself=False):
        return self.max_for_candidate(candidate, ignoreself=ignoreself) / 1.0 / self.max_for_all_candidates(ignoreself=ignoreself)
        
    #contributors    
    def total_for_contributor(self, contributor, ignoreself=False):
        return sum([c.amount * (ignoreself + c.contributor.klass !=1) for c in self.contributors[contributor]])

    def max_for_contributor(self, contributor, ignoreself=False):
        return max([c.amount * (ignoreself + c.contributor.klass !=1) for c in self.contributions if c.contributor == contributor])
        
    def max_for_all_contributors(self, ignoreself=False):
        return max([c.amount * (ignoreself + c.contributor.klass !=1) for c in self.contributions])

    def normalized_total_for_contributor(self, contributor, ignoreself=False):
        return self.max_for_contributor(contributor, ignoreself=ignoreself) / 1.0 / self.max_for_all_contributors(ignoreself=ignoreself)
        


if __name__ == '__main__':
    reader = csv.reader(open(sys.argv[1]))  # read in the CSV file
    conts = Contributions() #create the main object

    for row in [r for r in reader][1:]:  #skip the first line, assuming it is a CSV header
        cand = row[1]  # candidate's last name
        cont = row[3]  # contributor's name
        klass = int(row[5]) #class of contributor from legislation, with the addition of 0=candidate himself/herself
        amount = clean(row[4]) #amount of contribution
        
        candidate = Candidate(cand)
        contributor = Contributor(cont,klass)
        contribution = Contribution(candidate, contributor, amount)
        conts.add(contribution)


    #now let's produce the dot file
    #
    #after testing, orthoyx appears to be the best overlap method
    print '''graph G {

    graph [
    overlap="orthoyx",
    splines="true",
    margin=2,
    smoothing=true,
    remincross=true,
    dimen=10,
    mclimit=100,
    pad=0.5,
    fontname="DejaVu Sans 14",
    label="Campaign financing for City of North Vancouver 2008 elections -- http://jjensen.ca"

    ];

    '''

    #generate the boxes for all the candidates
    #width is based on the comparative size of total amount of donations to the candidate
    #for example:
    # Candidate     Total Amount Raised    Normalized Total
    # Arnold        $11,000                0.73
    # Barnston      $15,000                1.00
    # Callaghan	    $5,000                 0.33
    #
    # if ignoreself is True, ignore contributions from the candidates themselves, if False, then include them         
    print "node [shape=box];"
    for candidate in conts.candidates:
        print ''' %s [fixedsize=true, width=%s, label="%s"];''' % (candidate.nodename(),
                                                                   0.1 + conts.normalized_total_for_candidate(candidate, ignoreself=True),
                                                                   candidate.name)
        
        
    print
    #generate the nodes for all the contributors
    #width is based on the comparative size of total amount of all donations from the contributor, as per candidates above
    #this bit evolved as I was playing with the graphs, so there is cruft in here
    for contributor in conts.contributors:
        if contributor.klass not in [0, 1]:  #not from an individual or the candidate himself/herself
            if contributor.klass == 4: #a trade union
                shape = "triangle"
            else:
                shape = "circle" #a corporation
            print ''' %s [fixedsize=true, width=%s, height=%s, label="%s", fontsize=8, shape="%s"];''' % (contributor.nodename(),
                                                                               0.1 + conts.normalized_total_for_contributor(contributor, ignoreself=True),
                                                                               0.1 + conts.normalized_total_for_contributor(contributor, ignoreself=True),
                                                                               contributor.name.replace(" ","\\n"),
                                                                               shape)
        else:
            if contributor.name == 'Self': #just ignore contributions from candidates themselves
                continue
                name = "Self"
            else: #otherwise, must be just an individual
                name = ""  #set the label to be blank, otherwise the graph is unreadable
            print ''' %s [width=%s, height=%s, fixedsize=true, fontsize=8, shape=house, label="%s"];''' % (contributor.nodename_short(),
                                                                                                            0.1 + conts.normalized_total_for_contributor(contributor, ignoreself=False),
                                                                                                            0.1 + conts.normalized_total_for_contributor(contributor, ignoreself=False),
                                                                                                            name)
                                                                               
    print

    #now draw the edges between the candidates
    #penwidth (thickness) of the edge is factored by how it compares to the maximum of all contributions
    for cand in conts.candidates:
        print "subgraph %s {"  % cand.nodename()
        for c in conts.contributions:
            if cand == c.candidate:
                penwidth = 10 * (c.amount / 1.0 / conts.max_for_all_candidates())
                length = 1.0 / (1 + penwidth)
                if c.contributor.klass not in [0,1]:
                    print ''' "%s" -- "%s" [fontsize=8, penwidth=%s]; ''' % (c.contributor.nodename(),
                                                                               c.candidate.nodename(),
                                                                               penwidth)
                else:
                    if c.contributor.klass == 1:
                        print ''' "%s" -- "%s" [penwidth=%s, label=""]; ''' % (c.contributor.nodename_short(),
                                                                   c.candidate.nodename(),
                                                                   penwidth)
        print "}\n"
                    

    print "}"  #all done

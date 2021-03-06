##Author: Rene Pfitzner
##August 2013

#This module implements scientometrics multiplex structures using graph_tool

import graph_tool.all as gt
import csv
import itertools
import random

class PaperAuthorMultiplex():
    'Paper Citation and Author Collaboration Multiplex Structure'

#############################################################
    #Initialize empty object
    def __init__(self):
        
        #create empty multiplex structure
        self.collab = gt.Graph(directed=False)
        self.citation = gt.Graph(directed=True)
        self.citation.vertex_properties['year']=self.citation.new_vertex_property('int')
        self.citation.vertex_properties['_graphml_vertex_id']=self.citation.new_vertex_property('string')
        self.citation.edge_properties['year']=self.citation.new_edge_property('int')
        self.collab.vertex_properties['year']=self.collab.new_vertex_property('int')
        self.collab.vertex_properties['_graphml_vertex_id']=self.collab.new_vertex_property('string')
        self.collab.edge_properties['first_year_collaborated']=self.collab.new_edge_property('int')
        
    
        self._multiplex_collab = self.collab.new_vertex_property('object')
        self._multiplex_citation = self.citation.new_vertex_property('object')
        
        self._collab_graphml_vertex_id_to_gt_id = {}
        self._citation_graphml_vertex_id_to_gt_id = {}
    
    
################################################################
    ##
    #Function to add new papers, incl. collaborations
    def add_paper(self,paper_id,year,author_list,update_collaborations=True):
        '''Add a paper with paper_id (str), publication year (int) and authors specified in author_list (list<str>) to the multiplex. Collaborations are automatically updated, unless otherwise specified.'''
        
        #try whether paper exists already in citation network
        try:
            self._citation_graphml_vertex_id_to_gt_id[paper_id]
            raise PaperIDExistsAlreadyError() #stop execution here with this error
        except KeyError:
            pass
        
        #add new paper to citation network and additional data structures
        new_paper=self.citation.add_vertex()
        self._citation_graphml_vertex_id_to_gt_id[paper_id]=self.citation.vertex_index[new_paper]
        self.citation.vertex_properties['_graphml_vertex_id'][new_paper]=paper_id
        self.citation.vertex_properties['year'][new_paper]=int(year)
        self._multiplex_citation[new_paper]={}
        
        
        #add collaborations between authors on collab network
        if update_collaborations == True:
            #first add authors to collab network, if not there already
            for author in author_list:
                try:
                    new_author=self.collab.vertex(self._collab_graphml_vertex_id_to_gt_id[author])
                except KeyError:
                    new_author = self.collab.add_vertex()
                    self._collab_graphml_vertex_id_to_gt_id[author]=self.collab.vertex_index[new_author]
                    self.collab.vertex_properties['_graphml_vertex_id'][new_author]=author
                    self._multiplex_collab[new_author]={}
                #add multiplex information
                self._multiplex_collab[new_author][new_paper]=True
                self._multiplex_citation[new_paper][new_author]=True
                
            #add collaborations, if older, registered collaborations do not exist
            for author_comb in itertools.combinations(author_list,2):
                a1_gt_id = self._collab_graphml_vertex_id_to_gt_id[author_comb[0]]
                a2_gt_id = self._collab_graphml_vertex_id_to_gt_id[author_comb[1]]
                e = self.collab.edge(a1_gt_id,a2_gt_id)
                if e == None:
                    e = self.collab.add_edge(a1_gt_id,a2_gt_id)
                if self.collab.edge_properties['first_year_collaborated'][e]>int(year) or self.collab.edge_properties['first_year_collaborated'][e]==0:
                    self.collab.edge_properties['first_year_collaborated'][e]=int(year)        


################################################################
    ##
    #Funtion to add citation to citation network
    def add_citation(self,cited_paper,citing_paper):
        '''Add citation between two paper in citation network.'''
        try:
            cited_paper_gt=self._citation_graphml_vertex_id_to_gt_id[cited_paper]
        except KeyError:
            raise NoSuchPaperError()
            
        try:
            citing_paper_gt=self._citation_graphml_vertex_id_to_gt_id[citing_paper]
        except KeyError:
            raise NoSuchPaperError()

        if self.citation.edge(cited_paper_gt,citing_paper_gt)==None:
            new_citation=self.citation.add_edge(cited_paper_gt,citing_paper_gt)
            self.citation.edge_properties['year'][new_citation]=self.citation.vertex_properties['year'][self.citation.vertex(citing_paper_gt)]
        else:
            raise CitationExistsAlreadyError()
                 

################################################################    
    ##
    #Function to add plain new collaboration, independent of papers, from other sources
    def add_collaboration(self,author1, author2, year):
        '''Add collaboration between two authors'''
         
        for author in [author1,author2]:
            try:
                new_author=self._collab_graphml_vertex_id_to_gt_id[author]
            except KeyError:
                new_author = self.collab.add_vertex()
                self._collab_graphml_vertex_id_to_gt_id[author]=self.collab.vertex_index[new_author]
                self.collab.vertex_properties['_graphml_vertex_id'][new_author]=author
                self._multiplex_collab[new_author]={}
                            
        #add collaborations, if older, registered collaborations do not exist
        a1_gt_id = self._collab_graphml_vertex_id_to_gt_id[author1]
        a2_gt_id = self._collab_graphml_vertex_id_to_gt_id[author2]
        e = self.collab.edge(a1_gt_id,a2_gt_id)
        if e == None:
            e = self.collab.add_edge(a1_gt_id,a2_gt_id)
        if self.collab.edge_properties['first_year_collaborated'][e]>int(year) or self.collab.edge_properties['first_year_collaborated'][e]==0:
            self.collab.edge_properties['first_year_collaborated'][e]=int(year)
            

################################################################        
    ##
    #Function to read a multiplex from files
    def read_graphml(self,collab_file,citation_file,mult_file):
        '''Read multiplex from files specifying the collaboration network, the citation network and multiplex meta data'''

        ##################################
        #determine csv delimiter
        f=open(mult_file,'r')
        dialect=csv.Sniffer().sniff(f.readline())
        csv_delimiter=dialect.delimiter
        f.close()

        #read data
        self.collab = gt.load_graph(collab_file)
        self.citation = gt.load_graph(citation_file)
        self.citation.vertex_properties['year']=self.citation.new_vertex_property('int')

        #create the multiplex structure, implemented with property maps
        self._multiplex_collab = self.collab.new_vertex_property('object')
        self._multiplex_citation = self.citation.new_vertex_property('object')

        for v in self.collab.vertices():
            self._multiplex_collab[v]={}
        for v in self.citation.vertices():
            self._multiplex_citation[v]={}

        #since I do not know how to address a node in graph_tool using his properties, create a dictionary to have this info:
        self._collab_graphml_vertex_id_to_gt_id = {}
        self._citation_graphml_vertex_id_to_gt_id = {}

        for v in self.collab.vertices(): 
            self._collab_graphml_vertex_id_to_gt_id[self.collab.vertex_properties['_graphml_vertex_id'][v]]=int(self.collab.vertex_index[v])

        for v in self.citation.vertices(): 
            self._citation_graphml_vertex_id_to_gt_id[self.citation.vertex_properties['_graphml_vertex_id'][v]]=int(self.citation.vertex_index[v])

        #fill the multiplex
        with open(mult_file,'r') as f:
            #read header to determine property name
            header = f.readline()
            header = header.split(csv_delimiter)
            multiplex_edge_property_name = header[2].rstrip()

            #write multiplex edges with multiplex edge property (year)
            for line in f:
                tmp = line.split(csv_delimiter)
                paper_tmp = tmp[0]
                author_tmp = tmp[1]
                year = int(tmp[2].rstrip())

                try:
                    paper_obj = self.citation.vertex(self._citation_graphml_vertex_id_to_gt_id[paper_tmp])
                except KeyError:
                    v=self.citation.add_vertex()
                    self.citation.vertex_properties['_graphml_vertex_id'][v]=paper_tmp
                    self._multiplex_citation[v]={}
                    paper_obj = v

                try:
                    author_obj = self.collab.vertex(self._collab_graphml_vertex_id_to_gt_id[author_tmp])
                except KeyError:
                    v=self.collab.add_vertex()
                    self.collab.vertex_properties['_graphml_vertex_id'][v]=author_tmp
                    self._multiplex_collab[v]={}
                    author_obj = v
                    
                self.citation.vertex_properties['year'][paper_obj]=year

                self._multiplex_collab[author_obj][paper_obj] = True
                self._multiplex_citation[paper_obj][author_obj] = True

################################################################
    ##
    #Show all papers by one author
    def papers_by(self,author_id):
        '''Returns a list of paper (citation) vertex objects that specified author has (co)authored.'''
        try:
            author=self.collab.vertex(self._collab_graphml_vertex_id_to_gt_id[author_id])
            return self._multiplex_collab[author].keys()
        except KeyError:
            raise NoSuchAuthorError()
        
################################################################
    ##
    #Show all papers by one author
    def authors_of(self,paper_id):
        '''Returns a list of author (collaboration) vertex objects that have (co)authored the specified paper.'''
        try:
            paper=self.citation.vertex(self._citation_graphml_vertex_id_to_gt_id[paper_id])
            return self._multiplex_citation[paper].keys()
        except KeyError:
            raise NoSuchPaperError()
        

############################################################
    ##
    #Function to calculate socially biased citations
    def socially_biased_citations(self):
        '''Calculate number of socially-biased citations'''
        print 'Calculating socially biased citation statistics...'
        print '--------------'
        print 'Consider executing check_citation_causality() first!'
        for paper in self.citation.vertices():
            year = self.citation.vertex_properties['year'][paper]
            biased_citations=0
            self_citations=0
            citations=0
            authors = self._multiplex_citation[paper].keys()
            earlier_collaborators = []

            for a in authors:
                for n in a.all_neighbours():
                    if self.collab.edge_properties['first_year_collaborated'][self.collab.edge(a,n)]< year:
                        earlier_collaborators.append(n)
                
            for citing_paper in paper.out_neighbours():
                citations+=1
                citing_authors = self._multiplex_citation[citing_paper].keys()
                if set(authors).intersection(set(citing_authors)): #count self-citations
                    self_citations+=1
                if earlier_collaborators and set(earlier_collaborators).intersection(set(citing_authors)).difference(authors): #add biased citation if citing author is former coauthor of at least one of the authors; exclude self-citations here
                    biased_citations+=1

            print '--------------'
            print 'paper: '+self.citation.vertex_properties['_graphml_vertex_id'][paper]
            print 'citations: '+str(citations)
            print 'self citation: '+str(self_citations)
            print 'socially biased citations: '+str(biased_citations)
            
            
#################################################
#define Error Classes

class PaperIDExistsAlreadyError(Exception):
    pass
    
class NoSuchPaperError(Exception):
    pass
    
class NoSuchAuthorError(Exception):
    pass
    
class CitationExistsAlreadyError(Exception):
    pass


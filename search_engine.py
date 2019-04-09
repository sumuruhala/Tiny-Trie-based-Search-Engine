import re
from bs4 import BeautifulSoup
from collections import defaultdict
from urllib import request
import pickle

#---------------------------------------------------------------------------------
#   Global constants:
#---------------------------------------------------------------------------------

RGX = re.compile('(\w+|\d+)', flags=re.IGNORECASE)
OLDB_FILE = 'OLDB.txt'
TRIE_FILE = 'TRIE.pkl'
BUILD_INF_FILE = 'build_info.txt'
BLDINFF = open(BUILD_INF_FILE, 'w')

#---------------------------------------------------------------------------------
#   External Ocurrency List Array simulator:
#---------------------------------------------------------------------------------

class ExternalOLArray:
    def __init__(self, file_name):
        self.file = file_name
        self.array = []
        self.free_indices = set()

        # populate self.array and self.free_indices:
        with open(self.file, "r") as f:
            # to track the indices of blank lines
            idx = 0
            for line in f:
                line = line.strip()
                if len(line) == 0: # blank line for a new occurence list
                    self.free_indices.add(idx)
                    self.array.append(set())
                else:
                    self.array.append(set(line.split(',')))
                idx += 1
    
    def save(self):
        with open(self.file, "w") as f:
            for ol in self.array:
                occ_list = ''
                for occ in ol:
                    occ_list += occ + ','

                line = occ_list.rstrip(',') + '\n'
                f.write(line)

    def at(self, idx):
        if idx < 0 or idx >= len(self.array):
            raise IndexError
        return self.array[idx]

    def addOccur2OL(self, occ):
        if len(self.free_indices) > 0:
            free_idx = self.free_indices.pop()
        else:
            self.array.append(set()) # new OL line in OL array
            free_idx = len(self.array) - 1
        
        self.array[free_idx].add(occ)
        return free_idx

    def size(self):
        return len(self.array)

#---------------------------------------------------------------------------------
#   Trie search engine:
#---------------------------------------------------------------------------------

class TrieNode:
    def __init__(self, key='*', isExternal=False, idx=-1):
        self.key = key
        self.children = []
        self.bExtern = isExternal
        self.idx = idx
        self.rank = 0 # ranking mechanism; for seach use
    
    def getKey(self):
        return self.key

    def getChildren(self):
        return self.children

    def getIdx(self):
        return self.idx

    def setChildren(self, children):
        self.children = children

    def isExternal(self):
        return self.bExtern

    def resetNode(self, key, isExternal, idx):
        self.key = key
        self.bExtern = isExternal
        self.idx = idx

    def getTerminatingChild(self):
        for child in self.getChildren():
            if child.getKey() == '*':
                return (True, child)
        return (False, TrieNode()) # not found

    def isRoot(self):
        return not self.isExternal() and self.getKey() == '*'

    def incRank(self, inc=1):
        self.rank += inc

    def getRank(self):
        return self.rank



class CompressedTrie:
    def __init__(self, root, eola):
        self.root = root
        self.eola = eola # External OL Array

    def _get_or_insert(self, word, occ, node, refIsInserted=[]):
        ''' return: a matched external node '''
        if len(refIsInserted) > 0:
            refIsInserted[0] = True

        i = 0
        nk = node.getKey()
        while i < len(word) and i < len(nk):
            if word[i] != nk[i]: # first mismatch position
                break
            i += 1
        
        if len(word) == i:
            if i < len(nk): # word is a prefix of nk
                if node.isExternal():
                    sfx_node = TrieNode(key=nk[i:], isExternal=True, idx=node.getIdx())
                else: # internal
                    sfx_node = TrieNode(key=nk[i:])
                    sfx_node.setChildren(node.getChildren()[:])

                tc = TrieNode(isExternal=True, idx=self.eola.addOccur2OL(occ))
                node.resetNode(isExternal=False, key=nk[:i], idx=-1)
                node.setChildren([sfx_node, tc])
                return tc
            else: # exact match to an existing word in trie
                if node.isExternal(): # e.g. case fj8w903hr9ushdfg9f23
                    if len(refIsInserted) > 0:
                        refIsInserted[0] = False
                    return node
                
                # 'node' is internal:
                (has, tc) = node.getTerminatingChild()
                if not has: # 'node' has got children but none of them are terminating child (external)
                    # make the word complete in trie
                    tc = TrieNode(isExternal=True, idx=self.eola.addOccur2OL(occ))
                    node.getChildren().append(tc)
                else:
                    if len(refIsInserted) > 0:
                        refIsInserted[0] = False
                return tc
        elif len(nk) == i:
            if i < len(word): # nk is a prefix of word
                next_char = word[i]
                for child in node.getChildren():
                    if child.getKey()[0] == next_char:
                        return self._get_or_insert(word[i:], occ, child, refIsInserted) # recursively search & insert for remaining parts of the word
                
                if not node.isExternal(): # at least 2 children
                    # this word is a brand new word; no child was qualified to match remaining part of the word, hence needs to add a new external child
                    tc = TrieNode(key=word[i:], isExternal=True, idx=self.eola.addOccur2OL(occ)) # case fj8w903hr9ushdfg9f23
                    node.getChildren().append(tc)
                    return tc
                else: # external
                    n1 = TrieNode(isExternal=True, idx=node.getIdx()) # terminating node for original node.key
                    n2 = TrieNode(key=word[i:], isExternal=True, idx=self.eola.addOccur2OL(occ))

                    node.resetNode(isExternal=False, idx=-1, key=node.key) # make internal (key is not altered)
                    node.setChildren([n1, n2])
                    return n2
        elif i > 0: # word and nk have common prefix
            tc = TrieNode(isExternal=True, key=word[i:], idx=self.eola.addOccur2OL(occ))

            if node.isExternal():
                sfx_node = TrieNode(isExternal=True, key=nk[i:], idx=node.getIdx())
            else: # internal
                sfx_node = TrieNode(key=nk[i:])
                sfx_node.setChildren(node.getChildren()[:])

            node.resetNode(isExternal=False, key=nk[:i], idx=-1) # key is reset
            node.setChildren([tc, sfx_node])
            return tc
        
        # NO common prefix; shall be root

        if not node.isRoot():
            raise Exception
        
        # print("!!!!!!!!!!")
        for child in node.getChildren():
            if word[0] == child.getKey()[0]:
                return self._get_or_insert(word, occ, child, refIsInserted)
        
        # no child of root matches word; insert it
        tc = TrieNode(isExternal=True, key=word, idx=self.eola.addOccur2OL(occ))
        node.getChildren().append(tc)
        return tc

    def build(self, occ_doc, doc_words_list):
        wstr = ''
        for word in doc_words_list:
            isInsert = [True]
            node = self._get_or_insert(word, occ_doc, self.root, isInsert)

            if not isInsert[0]:
                self.eola.at(node.getIdx()).add(occ_doc) # update to include this (new) occurence doc

                wstr += "trie: '{}'(in {}) found in OL: {}\n".format(word, occ_doc, self.eola.at(node.getIdx()))
            else:
                wstr += "'{}'(in {}) -> trie\n".format(word, occ_doc)
            
        BLDINFF.write(wstr)
        BLDINFF.flush()

        self.eola.save() # write OLA to DB file
        with open(TRIE_FILE, 'wb') as tf:
            pickle.dump(self.root, tf)
        
    def _search(self, word, node):
        if node.isRoot() or len(word) == 0: # invalid inputs
            return (-1, -1)

        nk = node.getKey()
        if len(word) < len(nk): # word is impossible to exact match any node
            return (-1, -1)

        if '*' == nk:
            if not node.isExternal():
                raise Exception # internal node shall not have key '*'
            # was exact matched and now in its terminating child
            node.incRank()
            return (node.getIdx(), node.getRank()) # e.g. for case zbc9789g4hfshr38

        if word == nk: # exact match
            if node.isExternal():
                node.incRank()
                return (node.getIdx(), node.getRank())

            (has, tc) = node.getTerminatingChild()
            return self._search(word, tc) # case zbc9789g4hfshr38

        if len(word) == len(nk): # mismatch
            return (-1, -1)

        # need continue searching down trie:
        assert(len(word) > len(nk))
        i = 0
        while i < len(nk):
            if word[i] != nk[i]:
                return (-1, -1) # suffix [i:] of nk and word mismatched
            i += 1

        for child in node.getChildren():
            if child.getKey()[0] == word[i]:
                return self._search(word[i:], child)
        
        return (-1, -1)

    def search_include_any(self, words):
        uni = defaultdict(int) # {occ:rank}

        for word in words:
            for child in self.root.getChildren():
                if child.getKey()[0] != word[0]:
                    continue

                (idx, rank) = self._search(word, child)
                if idx > -1:
                    for occ in self.eola.at(idx):
                        uni[occ] += rank

        return sorted(uni, key=uni.get, reverse=True) # a list of occurences that their ranks are in decreasing order

    def search_include_all(self, words):
        intersec = set()
        isInit = True
        max_rank = 0
        max_rank_word = ''

        for word in words:
            for child in self.root.getChildren():
                if child.getKey()[0] != word[0]:
                    continue

                (idx, rank) = self._search(word, child)
                if idx > -1: # search hit
                    if rank > max_rank:
                        max_rank = rank
                        max_rank_word = word

                    if isInit:
                        intersec = self.eola.at(idx)
                        isInit = False
                    else:
                        intersec = intersec.intersection(self.eola.at(idx))
                    break # for child ... (this will skip outer "else:" clause!)

                return [] # never search hit, immediately get result
            else: # no child will match word
                return [] # immediately get result

        # ranking algorithm: the rank of 'occ' is its total occurence number of the most popular word
        m = defaultdict(int)
        global rc
        for occ in intersec:
            # (if necessary, download the 'occ' file here...)
            # inspect occ:
            with open(occ) as html_doc:
                soup = BeautifulSoup(html_doc, 'html.parser')
                html_text = soup.get_text()
                m[occ] = [word.lower() for word in RGX.findall(html_text) if word.lower() not in STOP_WORDS].count(max_rank_word)

        return sorted(m, key=m.get, reverse=True)

#---------------------------------------------------------------------------------
#   A sample operation of the trie search engine:
#---------------------------------------------------------------------------------

'''
    Build Trie from collected webpages
'''

STOP_WORDS = []
with open("stop_words.txt", 'r') as sw:
    wls = ''
    for line in sw.readlines():
        wls += line
    STOP_WORDS.extend(word.strip(',').lower() for word in wls.strip().split())
    # print(STOP_WORDS)

eola = ExternalOLArray(OLDB_FILE)
root = TrieNode()
isLoadTrie = False

with open(OLDB_FILE, 'r') as db:
    if len(db.read().strip()) > 0:
        isLoadTrie = True

if isLoadTrie:
    with open(TRIE_FILE, 'rb') as tf:
        root = pickle.load(tf)
        print("TRIE LOADED")

ct = CompressedTrie(root, eola)

doc_names = ['test_html1.html', 'test_html2.html', 'test_html3.html']
depth = 1 # just for example

for doc_name in doc_names:
    # print(doc_name)
    with open(doc_name) as html_doc:
        soup = BeautifulSoup(html_doc, 'html.parser')

        if depth > 0:
            depth -= 1
            for html_link in soup.find_all('a'):
                doc_names.append(html_link.get('href'))

        html_text = soup.get_text()
        words = [word.lower() for word in RGX.findall(html_text) if word.lower() not in STOP_WORDS]

        ct.build(doc_name, words)



'''
    Simulate user search
'''

user_input = input("Please input search word(s) (separate by whiltespaces) >>> ")
search_words = [word.lower() for word in user_input.strip().split()]

OPTION_STR = "Search mode -- 1: Including ANY word; 2: Including ALL word >>> "
choice = input(OPTION_STR)
while int(choice) not in [1,2]:
    choice = input(OPTION_STR)

# print("Words: ", search_words)
print("Results:")
mode = int(choice)
if mode == 1:
    res = ct.search_include_any(search_words)
else:
    res = ct.search_include_all(search_words)

if len(res) == 0:
    print('\t:( Your search - {} ({}) - did not match any documents.'.format(search_words, 'Include ANY' if mode == 1 else 'Include ALL'))
else:
    for i, item in enumerate(res):
        print('\t({}) '.format(i) + item)

BLDINFF.close()
## Tiny-Trie-based-Search-Engine


#1. I used the compressed trie which each node holds a substring as a key.

    Data structures:
    
        The nodes are 2 types: external or interal.
    
        To enable to build trie tree, each nodes hold: key(substring or '*') of its node, its children list, ranking helper field,
        and an index field to indicate the place in the external Occurency List Array (OLDB).
    
        External nodes may hold a suffix of the string represented along the path, or hold a special character key '*' (I call it "Terminating Child" in code)
        to indicate that this node up to the topmost internal node along with its path represents a string that terminates with a suffix(key) of this
        external node's parent.
        
        Internal nodes may hold a substring of some words.
    
    How the program work:
    
        Building/Recovering trie:
            Given the stop words and collected html files (including link and hierarchy), I extract and simply preprocessed the collected words to get
            ready for building the trie. I insert each word one by one and the trie has built in an infomation-dump mechanism so that we can inspect the
            behavior of the trie-building. After the trie is built, it is saved to disk file so that next time we don't need to reconstruct those words
            that already built; we can just reload the trie constructed by previous run of the application (So that we can only provide new files to the
            program to add new words and/or their occurencies). To rebuild the trie, see below section 3.
            
        External OL array (EOLA):
            I define a class for holding the array in runtime. When building the trie EOLA will be simultaneously updated to reflect the newest trie-EOLA
            relationship. The EOLA is saved to disk file similar as well, so that next time trie and EOLA all can be loaded to immediately get ready to
            work for updating/searching.
            
        Ranking:
            Whenever the user search a word and that word search-hit in the trie, I will increase the corresponding occrency's ranking by 1. E.g. for
            'my_word':{'f1.html', 'f2.html'} with rank 2 (Note: it is for each file), after 1 more seach of 'my_word', the rank will be 3. Thus the more
            user search reaches a specific occrency file the more the file will become 'popular'.
            
            I define that:
            For a search query of "Including Any Word" mode, I accumulate/sum-up the specific occurency file rank whenever its key/word
            hits.  E.g. if two consecutive search all reached 'f1.html' with its rank=100, then its cummulative rank will increased by 100 + 100 = 200 Thus the more a file hits in one search the larger it ranked. Finally I output the resulting file list with decreasing ranking order.
            
            For a search query of "Including All Words" mode, after I calculated the intersection of the hit files, I again inspect those file to count
            how many times the most-ranked word (among the search words given) appears in each of these files. Then I sort those files with by these
            counts.
            
        Searching (User):
            The user can input a list of search words and then I preprocess them to ready to search in trie.
            The user shall select which search mode: Include ANY or Include ALL.
            If the trie cannot find any document, then it will print a google-like message to the user. Otherwise,
            the files are listed using the ranking mechanism above.
        
#2. The program code are all in "search_engine.py".
    
#3.
    OLDB.txt:
    The disk file to keep EOLA.
    NOTE: To reset/rebuild the trie (so that you can run the program as if at 1st time), you shall clear all contents in this file.
    
    stop_words.txt:
    The listing of the stop words to exclude from search.
    
    test_html(1-3).html:
    The sample input webpages.
    
    folder:
    The folder containing another sample webpage which is linked('href=') from the outer sample webpages.
        
    TRIE.pkl:
    Python.pickle's dump file containing the up-to-date entire trie structure. It is read and trie is loaded into the program in following runnings of the program.
    
#4.
    build_info.txt:
    The trie building dumped messages. As a sample of non-1st-time running of the program, you can see the contents are all begining with "trie: ",
    which means that as long as we do not insert new word to trie, the trie is reusing the words info in EOLA.
    
    build_info_1st_time_built.txt:
    The sample output of trie building for the 1st-time run. You can see many "-> trie" which means that trie is keep constructing with new words.
    
    Please see some other screenshots in the project folder.
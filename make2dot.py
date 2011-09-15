#!/usr/bin/env python

import sys
import re
import os
import pymake.parser

print "digraph makefile_graph {"
print "rankdir=LR;"
print "node [shape = rectangle];"

prevDict = {}
dotDict = {}
variableDict = {}
valueDict = {}

colon = re.compile(':')
variable = re.compile(r'(.*):(?:.*) \$\((.*)\)(?:.*)')
substitutions = re.compile(r'(?:.*) \$\((.*)\)(?:.*)')

lastSeen = False
filelist = []
makefilepath = ""

# Go through the Makefile and keep track of all includes
for f in sys.argv[1:]:
    fd = open(f, 'rU')
    prefix = str(os.path.dirname(f))
    s = fd.read()
    fd.close()
    stmts = pymake.parser.parsestring(s, f)
    ans = str(stmts)
    fileSplit = ans.split('\n');
    for line in fileSplit:
        # Find all user variables and put them into valueDict
        if(line.startswith("Include Exp")):
            filename = line[line.find("(")+1:line.find(")")]
            filename = filename.replace("'","")
            filename = filename.strip()
            filename = prefix + "/" +filename 
            filelist.append(filename)
    filelist.append(f)

# This loop find all the rules and any variables in its dependencies
for f in filelist:
    try:
        fd = open(f, 'rU')
    except:
        continue
    s = fd.read()
    sArray = s.split('\n')
    fd.close()
    parts = ""
    for line in sArray:
        if len(line) == 0 or line[0] in ['\t', '#'] or line.find('=') > 0 or line.find('?') > 0:
            continue
        parts = colon.split(line)
        if len(parts) == 1:
            continue
        elif len(parts) == 2:
            m = variable.match(line)
            if m is not None:
                rule = str(m.group(1))
                var = str(m.group(2))
                variableDict[rule] = var

#Call the PyMake parser with the given makefile
for f in filelist:
    try:
        fd = open(f, 'rU')
    except:
        continue
    s = fd.read()
    fd.close()
    stmts = pymake.parser.parsestring(s, f)
    ans = str(stmts)
    fileSplit = ans.split('\n');
    for line in fileSplit:
        # Find all user variables and put them into valueDict
        if(line.startswith("SetVariable") and "+=" not in line):
            lastSeen = True 
            rule = line[line.find("(")+1:line.find(")")]
            rule = rule.replace("'","")
            rule = rule.strip()
            continue
        if(lastSeen == True):
            line = line.replace("'","")
            line = line.replace("\"","")
            line = line.strip()
            m = substitutions.match(line)
            if m is not None:
                try:
                    line = line.replace("$("+m.group(1)+")",valueDict[m.group(1)])
                except:
                    line = line.replace("$("+m.group(1)+")"," ")
            lastSeen = False 
            valueDict[rule] = line
 
        # Find all rules from output of PyMake

        if(line.startswith("Rule Exp")):
            lineSplit = line.split(": ")
            first = lineSplit[0]
            second = lineSplit[1]
            if len(lineSplit) > 2:
                third = lineSplit[2]
            rule = first[first.find("(")+1:first.find(")")]
            rule = rule.replace("'","")
            rule = rule.strip()
            if(second.startswith("<Expansion")):
                dep = third[third.find("[")+1:third.find(",")]
            else:
                dep = second[second.find("(")+1:second.find(")")]
            dep = dep.replace("'","")
            dep = dep.strip();             

            # Find all rules and all corresponding dependencies and split them and treat individually           

            origrule = rule
            if(len(origrule)>0):
                ruleSplit = rule.split(' ')
                for rule in  ruleSplit:
                    ruleLabel = rule
                    ruleLabel = ruleLabel.replace(".","")
                    ruleLabel = ruleLabel.replace("/","")
                    ruleLabel = ruleLabel.replace("-","")

                    if(len(dep)>0):
                        try:
                            extras = variableDict[rule]
                            dep = dep + " "+valueDict[extras]
                        except KeyError:
                            rule = rule    
                        depSplit = dep.split(' ')

                        # Handling IMPLICIT rules                 

                        if("SUFFIXES" in ruleLabel):
                            target = depSplit[0]
                            source = depSplit[1]                        
             
                            # Connect the new node to the old nodes which are already present

                            for dotRules in dotDict:
                                if(source in dotRules):
                                    sourceLabel = dotRules
                                    sourceLabel = sourceLabel.replace(".","")
                                    sourceLabel = sourceLabel.replace("/","")
                                    sourceLabel = sourceLabel.replace("-","")

                                    targetLabel = dotRules.replace(source,target)
                                    targetLabel = targetLabel.replace(".","")
                                    targetLabel = targetLabel.replace("/","")
                                    targetLabel = targetLabel.replace("-","")
                                    print sourceLabel+" [label=\""+dotRules+"\"];"
                                    print targetLabel+" [label=\""+dotRules.replace(source,target)+"\"];"
                                    print sourceLabel + "->" + targetLabel + ";"
         
                        # Loop through every dependency one by one             

                        for depFile in depSplit:
                            if("%" in depFile):
                                tempRule = rule.replace("%","(.*)")
                                tempRule = tempRule.replace("/","")
                                ruleRegex = re.compile(tempRule)

                                for k,v in dotDict.items():
                                    m = ruleRegex.match(k)
                                    if(m is not None):
                                        sourceLabel = k
                                        sourceLabel = sourceLabel.replace(".","")
                                        sourceLabel = sourceLabel.replace("/","")
                                        sourceLabel = sourceLabel.replace("-","")
                                        sourceLabel = sourceLabel.replace("%","")

                                        depFile = depFile.replace("/","") 
                                        tempDepFile = depFile.replace("%",m.group(1))

                                        targetLabel = tempDepFile.replace("/","")
                                        targetLabel = targetLabel.replace(".","")
                                        targetLabel = targetLabel.replace("-","")
                                        targetLabel = targetLabel.replace("%","")
                                        depFilePathSplit = os.path.split(tempDepFile) 
                                        if depFilePathSplit[1] in os.listdir(os.path.dirname(os.path.abspath(f))+"/"+depFilePathSplit[0]):
                                            sourceLabel = sourceLabel
                                            print sourceLabel+" [label=\""+k+"\"];"
                                            print targetLabel+" [label=\""+tempDepFile+"\"];"
                                            print sourceLabel + "->" + targetLabel + ";"
                            if((depFile.find(".")==-1 or depFile.find(".")==0 ) and "%" not in depFile):
                                prevDict[depFile] = rule;   
                            elif(rule.find(".")!=-1 and depFile.find(".")!=-1 and depFile.find(".")!=0 and "%" not in depFile and len(depFile)>0):
                                try:
                                    prevRule = prevDict[rule]
                                    del prevDict[rule]
                                    rule = prevRule
                                    ruleLabel = rule
                                    ruleLabel = ruleLabel.replace(".","")
                                    ruleLabel = ruleLabel.replace("/","")
                                    ruleLabel = ruleLabel.replace("-","")
                                except KeyError:
                                    rule = rule
                                print ruleLabel+" [label=\""+rule+"\"];"
                                depLabel = depFile
                                depLabel = depLabel.replace(".","")
                                depLabel = depLabel.replace("/","")
                                depLabel = depLabel.replace("-","")        
                                print depLabel+" [label=\""+depFile+"\"];"
                                print ruleLabel + "->" + depLabel + ";"
          
                                # Put the rule in dotDict for later use

                                dotDict[rule] = 1
                                dotDict[depFile] = 1
                            elif(rule.find(".")==-1 and depFile.find(".")!=-1 and depFile.find(".")!=0 and "%" not in depFile and len(depFile)>0):   
                                try:
                                    prevRule = prevDict[rule]
                                    del prevDict[rule]
                                    rule = prevRule
                                    ruleLabel = rule
                                    ruleLabel = ruleLabel.replace(".","")
                                    ruleLabel = ruleLabel.replace("/","")
                                    ruleLabel = ruleLabel.replace("-","")

                                    print ruleLabel+" [label=\""+rule+"\"];"
                                    depLabel = depFile
                                    depLabel = depLabel.replace(".","")
                                    depLabel = depLabel.replace("/","")
                                    depLabel = depLabel.replace("-","")
                                    print depLabel+" [label=\""+depFile+"\"];"
                                    print ruleLabel + "->" + depLabel + ";"

                                    # Put the rule in dotDict for later use

                                    dotDict[rule] = 1
                                    dotDict[depFile] = 1
                                except KeyError:
                                    rule = rule
                    preRule = rule      
print "}"

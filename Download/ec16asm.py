import sys
import re
import os
from pathlib import Path

# table of all instructions and their (basic) opcode
instructions : tuple = (('add', 'a', '#U8', '0x4300'),
                        ('addc', 'a', '#U8', '0x4100'),
                        ('and', 'a', '#U8', '0x4C00'),
                        ('brcc', '#S8', '', '0xC000'),
                        ('brcs', '#S8', '', '0xC400'),
                        ('brnc', '#S8', '', '0xC200'),
                        ('brns', '#S8', '', '0xC600'),
                        ('broc', '#S8', '', '0xC100'),
                        ('bros', '#S8', '', '0xC500'),
                        ('brzc', '#S8', '', '0xC300'),
                        ('brzs', '#S8', '', '0xC700'),
                        ('calld', '#U16', '', '0xA100'),
                        ('calli', '#U8', '', '0xA300'),
                        ('clr', 'c','', '0x1000'),
                        ('clr', 'ie','', '0x0200'),
                        ('clr', 'int','', '0x0400'),
                        ('cmp', 'a', '#U8', '0x4400'),
                        ('dec', '#U8', '', '0x4600'),
                        ('inc', '#U8', '', '0x4700'),
                        ('jmpd', '#U16', '', '0xA000'),
                        ('jmpi', '#U8', '', '0xA200'),
                        ('mov', '#U8', 'a', '0x1600'),
                        ('mov', 'a', '#U8', '0x5000'),
                        ('mov', 'a', 'status', '0x1400'),
                        ('mov', 'flags', 'a', '0x1200'),
                        ('mov', 'imask', 'a', '0x0500'),
                        ('mov', 'sp', 'a', '0x1300'),
                        ('load', '#U8', '#U16', '0x6100'),
                        ('load', 'a', '#U16', '0x6000'),
                        ('movi', '#U8', 'a', '0x5200'),
                        ('movi', 'a', '#U8', '0x8000'),
                        ('movxi', '#U8', 'a', '0x8200'),
                        ('movxi', 'a', '#U8', '0x8300'),
                        ('nop', '', '', '0x0000'),
                        ('not', 'a', '', '0x2F00'),
                        ('or', 'a', '#U8', '0x4D00'),
                        ('pop', 'a', '', '0x5100'),
                        ('push', 'a', '', '0x1500'),
                        ('reti', '', '', '0x8500'),
                        ('rets', '', '', '0x8400'),
                        ('rol', 'a', '', '0x2800'),
                        ('ror', 'a', '', '0x2900'),
                        ('set', 'c', '', '0x1100'),
                        ('set', 'ie', '', '0x0300'),
                        ('shl', 'a', '', '0x2A00'),
                        ('shr', 'a', '', '0x2B00'),
                        ('sub', 'a', '#U8', '0x4200'),
                        ('subb', 'a', '#U8', '0x4000'),
                        ('swap', 'a', '', '0x2500'),
                        ('xor', 'a', '#U8', '0x4E00'))

# named constants for columns of table 'instructions'
I_MNE = 0
I_ARG1 = 1
I_ARG2 = 2
I_OPC = 3

# list of mnemonics extracted from column 0 of 'instructions'
mnemonics : list = []
# list of first arguments extracted from column 1 of 'instructions'
args1 : list = []
# list of second arguments extracted from column 2 of 'instructions'
args2 : list = []

# these entries in columns 1 and 2 are treated specially
special_args : tuple = ('', '#S8', '#U8', '#U16')

# tuple of number arguments
num_args : tuple = ('#S8', '#U8', '#U16')

# each instruction gets assigned a calculated number to identify it
fingerprint : list = []

# table of assembler directives
directives : tuple = ('org_e', 'org_i', 'equ', 'res_i', 'res_e', 'dw_e')

# two arrays with reserved names
named_args : tuple = ()
mnemonics_and_directives : tuple = ()

# each source file is first read into 'single_source' and converted to all lower case
single_source : list = []  
# by resolving the includes all source files are aggregated in 'full_source'
full_source : list = []     

# the pure source code is extracted from 'full_source' into 'code'
code : list = []    

# named constants for columns of array 'code'
# 0 - 4  : source code
C_LNUM = 0		# line number of source code
C_LBL = 1		# label (address of the EC16)
C_MNE = 2		# mnemonic
C_ARG1 = 3		# first argument
C_ARG2 = 4		# second argument
# 5 - 9 : assembler temporary output
C_OLT = 5		# flag for linker 
C_ADDR = 6		# address of the EC16
C_OPC = 7		# full resp. upper half of opcode
C_OPCLO = 8		# lower half of opcode (#S8/#U8)
C_ARG = 9		# #U16 argument


lbl_line : list = []       # list of source code line numbers where labels are defined
lbl_name : list = []       # list of label names
lbl_value : list = []      # list of label values

filename : str = ""
list_of_filenames : list = [] # list of included files to avoid multiple inclusions
listing_name : str = ""  # name of first asm file but with extension .lst

line : list = []  #holds current source code line
linenum : int = 0  # holds number of current source code line

extmem_cnt : int = 0  # counter for external memory location (0..65535)
intmem_cnt : int = 0  # counter for internal memory location (0..255)



def readsourcefile(file):  #read source file into 'single_source', convert to lower case
    global linenum
    try:
        with open(file, "rt", encoding='UTF-8') as f:
            # simply read in source file and convert it to lower case
            for sourceline in f:
                # sourceline = sourceline.lower()
                single_source.append(sourceline)
    except FileNotFoundError:
        # if the first ('main') file is not found, only error message
        if full_source == []:
            print('Error opening first asm file! File "' + file + '" not found.')
            sys.exit()
        # if one of the include files not found, error message plus listing
        else:
            with open(listing_name, 'w', encoding="utf-8") as listing:
                listing.writelines(full_source)
            print('Error gathering asm files! Include file "' + file + '" not found.')
            print('See file "' + listing_name + '" at line '  + str(linenum+1))
            print(full_source[linenum])
            sys.exit()


# scan 'full_source' for 'include' directives
def find_include():  

    global linenum, filename

    asmlinesplit = []
    # scan full_source from linenum onwards
    for i, asmline in enumerate(full_source[linenum:]):
        asmline = asmline.strip()
        # remove comments
        asmline = asmline.split(';', 1)[0]
        if asmline[0:7] == 'include':
            linenum += i
            asmlinesplit = [p for p in re.split("(\\s|\\\".*?\\\"|'.*?')", asmline) if p.strip()]
            if len(asmlinesplit) < 2:
                with open(listing_name, 'w', encoding="utf-8") as listing:
                    listing.writelines(full_source)
                print('Error in INCLUDE directive!')
                print('See file "' + listing_name + '" at line '  + str(linenum+1))
                print(full_source[i])
                sys.exit()
            filename = asmlinesplit[1]
            return True 
    return False


def getnum(number):
    try:
        value=int(number, 0)
    except (TypeError, ValueError):
        print('Error: Integer expected. (Perhaps label not defined?)')
        print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
        print(full_source[line[C_LNUM] - 1])
        sys.exit()
    if 0 <= value <=65535 : 
        return value
    print('Error: Number too big, must be 0 .. 65535')
    print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
    print(full_source[line[C_LNUM] - 1])
    sys.exit()
   


def testnum(number):
    try:
        int(number, 0)
    except (TypeError, ValueError):
        return False

    return True


def is_valid_label(label) : 

    labelstart = label[:1]
    if labelstart.isnumeric() :
        return False

    for char in label :
        if not char.isalnum() and char != '_' :
            return False
    
    return True


def add_to_code():
    global linenum, extmem_cnt
    
    # calculate value to check against table 'fingerprint'
    fp = mnemonics.index(line[C_MNE]) * 65536

    if line[C_ARG1] != '':
        if testnum(line[C_ARG1]) or (line[C_ARG1] in lbl_name):
            fp += 256
        elif line[C_ARG1] in args1:
            fp += (args1.index(line[C_ARG1]) + 2) * 256
    if line[C_ARG2] != '':
        if testnum(line[C_ARG2]) or (line[C_ARG2] in lbl_name):
            fp += 1
        elif line[C_ARG2] in args2:
            fp += (args2.index(line[C_ARG2]) + 2)


    if fp not in fingerprint:
        print('Error! Unknown instruction')
        print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
        print(full_source[line[C_LNUM] - 1])
        sys.exit()

    # if applicable update labellist
    if line[C_LBL] in lbl_name :
        lbl_value[lbl_name.index(line[C_LBL])] = extmem_cnt

    # get index to 'instructions'
    instr_idx = fingerprint.index(fp)

    # add address
    code[linenum][C_ADDR] = '0x%04X' % extmem_cnt
    extmem_cnt += 1
    # add basic opcode
    code[linenum][C_OPC] = instructions[instr_idx][I_OPC]

    # arg1
    opc_lt = instructions[instr_idx][I_ARG1]
    if (opc_lt == '#S8') or (opc_lt == '#U8') :
        code[linenum][C_OPCLO] = line[C_ARG1]
        code[linenum][C_OLT] = opc_lt
    elif (opc_lt == '#U16') :
        code[linenum][C_ARG] = line[C_ARG1]
        extmem_cnt += 1
    
    # arg2
    opc_lt = instructions[instr_idx][I_ARG2]
    if opc_lt == '#U8' :
        code[linenum][C_OPCLO] = line[C_ARG2]
        code[linenum][C_OLT] = opc_lt
    elif (opc_lt == '#U16') :
        code[linenum][C_ARG] = line[C_ARG2]
        extmem_cnt += 1
        
    if testnum(code[linenum][C_OPCLO]) == True:
        code[linenum][C_OPCLO] = '0x%04X' % getnum(code[linenum][C_OPCLO])

    if testnum(code[linenum][C_ARG]) == True:
        code[linenum][C_ARG] = '0x%04X' % getnum(code[linenum][C_ARG])

    # print(code[linenum])


def exec_directive():
    global extmem_cnt, intmem_cnt

    # EQU
    if line[C_MNE]=='equ':
        if len(line)!=4:
            print('Error in EQU directive!')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
        value = getnum(line[C_ARG1])
        if value < 0 or value > 65535:
            print('Error: Value out of range 0..65535')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
        # search index of linenumber in list lbl_line
        # write value to list lbl_value at index
        idx=lbl_line.index(line[C_LNUM])
        lbl_value[idx]=value
     
    # ORG_E
    elif line[C_MNE]=='org_e':
        if len(line)!=4:
            print('Error in ORG_E directive!')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
        if line[C_ARG1] in lbl_name:
            idx = lbl_name.index(line[C_ARG1])
            value = lbl_value[idx]
            if value == -1:
                print('Error: Label value has to be defined before usage')
                print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
                print(full_source[line[C_LNUM] - 1])
                sys.exit()
        else:
            value = getnum(line[C_ARG1])
        if value < 0 or value > 65535:
            print('Error: Value out of range 0..65535')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
        
        if value < extmem_cnt:
            print('Error: address counter must not be set back')
            print('Current value : ' + '0x%04X' % extmem_cnt + '   New value : ' + '0x%04X' % value)
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
            
        extmem_cnt = value

    # ORG_I
    elif line[C_MNE]=='org_i':
        if len(line)!=4:
            print('Error in ORG_I directive!')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
        if line[C_ARG1] in lbl_name:
            idx = lbl_name.index(line[C_ARG1])
            value = lbl_value[idx]
            if value == -1:
                print('Error: Label value has to be defined before usage')
                print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
                print(full_source[line[C_LNUM] - 1])
                sys.exit()
        else:
            value = getnum(line[C_ARG1])
        if value < 0 or value > 255:
            print('Error: Value out of range 0..255')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()

        intmem_cnt = value


    # RES_I
    elif line[C_MNE]=='res_i':
        if len(line)!=4:
            print('Error in RES_I directive! Wrong number of arguments')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
        # get the number of words to reserve
        # Must be an integer or
        if testnum(line[C_ARG1]) == True :
            value = getnum(line[C_ARG1])
        # an already defined label
        elif line[C_ARG1] in lbl_name :
            value = lbl_value[lbl_name.index(line[C_ARG1])]
        if value == -1 :
            print('Error: Argument must be an integer or an already defined label')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()

        # add own label value to label list
        if line[C_LBL] in lbl_name:
            idx = lbl_name.index(line[C_LBL])
            lbl_value[idx]=intmem_cnt

        intmem_cnt+=value
        if intmem_cnt > 256:
            print('Error: Exceeded INTMEM range 0..255')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]) + ' or previous')
            print(full_source[line[C_LNUM] - 1])
            sys.exit()

    
    # RES_E
    elif line[C_MNE]=='res_e':
        if len(line)!=4:
            print('Error in RES_E directive! Wrong number of arguments')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
        # insert current EXTMEM address for listing
        line[C_ARG1:C_ARG1]=['0x%04X' % extmem_cnt]
        # get the number of words to reserve
        # Must be an integer or
        if testnum(line[C_ARG2]) == True :
            value = getnum(line[C_ARG2])
        # an already defined label
        elif line[C_ARG2] in lbl_name :
            value = lbl_value[lbl_name.index(line[C_ARG2])]
        if value == -1 :
            print('Error: Argument must be an integer or an already defined label')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()

        # add own label value to label list
        if line[C_LBL] in lbl_name:
            idx = lbl_name.index(line[C_LBL])
            lbl_value[idx]=extmem_cnt

        
        extmem_cnt+=value
        if extmem_cnt > 65536:
            print('Error: Exceeded EXTMEM range 0..65535')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]) + ' or previous')
            print(full_source[line[C_LNUM] - 1])
            sys.exit()

    
    #'DW_E'
    elif line[C_MNE]=='dw_e':
        dw_e_len = len(line)

        if dw_e_len <4:
            print('Error in DW_E directive! No arguments found.')
            print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
            print(full_source[line[C_LNUM] - 1])
            sys.exit()
 
        # update labellist
        if line[C_LBL] in lbl_name :
            lbl_value[lbl_name.index(line[C_LBL])] = extmem_cnt
            
        line.append('0x%04X' % extmem_cnt)
        
        for x in line[C_ARG1:dw_e_len] :
            if testnum(x) == True :
                value = getnum(x)
                if value < 0 or value > 65535:
                    print('Error: Value out of range 0..65535')
                    print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
                    print(full_source[line[C_LNUM] - 1])
                    sys.exit()
                line.append('0x%04X' % value)
                extmem_cnt += 1
            elif x in lbl_name :
                value = lbl_value[lbl_name.index(x)]
                line.append('0x%04X' % value)
                extmem_cnt += 1
            else :
                if x[0]=='"' and x[-1]=='"' and len(x)>2:
                    for c in x[1:-1]:
                        value = ord(c)
                        line.append('0x%04X' % value)
                        extmem_cnt += 1
                else:
                    print('Error: Invalid argument')
                    print('See file "' + listing_name + '" at line '  + str(line[C_LNUM]))
                    print(full_source[line[C_LNUM] - 1])
                    sys.exit()
        
        del line[C_ARG1:dw_e_len]

    return


# ################################################################################
# ################################################################################

# ---  Setup assembler : create lists from table of instructions ---
# ##################################################################

# from table 'instructions' extract mnemonics, args1 and args2
for instr in instructions:
    if instr[I_MNE] not in mnemonics:
        mnemonics.append(instr[0])
    if (instr[I_ARG1] not in args1) and (instr[I_ARG1] not in special_args):
        args1.append(instr[I_ARG1])
    if (instr[I_ARG2] not in args2) and (instr[I_ARG2] not in special_args):
        args2.append(instr[I_ARG2])

# create a numerical fingerprint for each instruction
for instr in instructions:
    # each instruction has a mnemonic, so start with 0
    fp = mnemonics.index(instr[I_MNE]) * 65536
    # 'special_args' count as zero, so start with 1
    if instr[I_ARG1] != '':  # '' counts as zero
        if instr[I_ARG1] in num_args:
            fp += 256
        else:
            fp += (args1.index(instr[I_ARG1]) + 2) * 256
    if instr[I_ARG2] != '':  # '' counts as zero
        if instr[I_ARG2] in num_args:
            fp += 1
        else:
            fp += (args2.index(instr[I_ARG2]) + 2)
    fingerprint.append(fp)
    #print(instr, fp)
# Debug! Should only be invoked when making changes to 'instructions'
# that lead to duplicate fingerprints
if len(fingerprint) != len(set(fingerprint)):
    print('Error! Instructions table is equivocal')

# fill the two arrays with reserved strings  
named_args = tuple(set(args1 + args2))
mnemonics_and_directives = tuple(mnemonics) + directives

# Say Hello
print('\nEC16ASM  V1.0.1 08-Feb-2025 -  Assembler for the EC16 microprocessor\n')


# ---  Step 1 : read all source code into 'full_source' and create listing  ---
# #############################################################################

# open the 'main' ASM file mentioned in the command line
if len(sys.argv) == 2:
    filename = sys.argv[1]
    # register the filename to avoid repeated inclusions
    list_of_filenames.append(os.path.abspath(filename))
    # derive the filename for the listing with the complete source code
    # e.g. mainfile.asm -> mainfile.lst
    listing_name = Path(filename).stem + '.lst'
else:
    print('Error in command line! Usage: ec16asm.py "mainfile.asm"')
    sys.exit()
    
readsourcefile(filename)  #read the 'main' source file into list 'single_source'
full_source = single_source  #copy 'single_source' into 'full_source'
single_source = []  #empty 'single_source' for possible include files

#scan 'full_source' for include directive
while find_include() == True :
    # include directive found, so comment it out and mark it with '; -> '
    full_source[linenum] = '; -> ' + full_source[linenum]
    filename = filename.strip('\"')
    # ensure that no file is included more than once
    if os.path.abspath(filename) not in list_of_filenames:
        # read include file into 'single_source'
        readsourcefile(filename)
        linenum += 1
        # insert include file into 'full_source' 
        full_source[linenum:linenum] = single_source
        # mark the end of the include file
        endmarker = '; -> end of included file "' + filename + '"\n'
        linenum_temp = linenum+len(single_source)
        full_source[linenum_temp:linenum_temp] = [endmarker]
        single_source = []  #empty 'single_source' for possible next include files
        # register the filename
        list_of_filenames.append(os.path.abspath(filename))
        # linenum += 1
    else:
        # if the file is already included only add a comment
        linenum += 1
        full_source[linenum:linenum] = ['; -> ignored since already included\n']
        linenum += 1

# all source files are now combined in 'full_source', so write it as listing 
with open(listing_name, 'w', encoding="utf-8") as listing:
    listing.writelines(full_source)


# ---  Step 2 : filter 'full_source' for pure source code and put it into 'code' ---
#      Create lists with labels, line numbers, and values
# ##################################################################################

for linenum, asmline in enumerate(full_source):
    # remove comments
    asmline = asmline.split(';', 1)[0]
    # remove leading and trailing white space chars
    asmline = asmline.strip()
    # if line is now empty, discard it
    if (not asmline):
        continue

    # create list of tokens (labels, mnemonics & arguments)
    asmlinesplit = [p for p in re.split("(\\s|\\\".*?\\\"|'.*?')", asmline) if p.strip()]

    # for 'dw_e' only the label and dw_e itself must be converted to lowercase
    # while a possible text argument must not
    if (len(asmlinesplit) > 2) and (asmlinesplit[0].lower() == 'dw_e'):
        asmlinesplit[0] = asmlinesplit[0].lower()
    elif (len(asmlinesplit) > 3) and (asmlinesplit[1].lower() == 'dw_e'):
        asmlinesplit[0] = asmlinesplit[0].lower()
        asmlinesplit[1] = asmlinesplit[1].lower()
   # all other tokens are converted to lowercase
    else:
        for num, token in enumerate(asmlinesplit):
            asmlinesplit[num] = token.lower()

    # add line number for reference and linkage
    asmlinesplit[0:0]=[linenum+1]

    # if the mnemonic is not preceded by a label...
    if asmlinesplit[1] in mnemonics_and_directives:
        # insert an empty string in front of it
        asmlinesplit[1:1]=['']
    #else test if label is valid
    elif (asmlinesplit[1] not in named_args):
        # label already existing?
        if asmlinesplit[1] in lbl_name:
            print('Error: redeclaration of label')
            print('See "' + listing_name + '" at line '  + str(linenum+1))
            print(full_source[linenum])
            sys.exit()            
        # label must not be the only string in a line
        if len(asmlinesplit) < 3:
            print('Error: Orphaned Label. See "' + listing_name + '" at line '  + str(linenum+1))
            print(full_source[linenum])
            sys.exit()
        # Test for valid label then add line number and label to resp. list
        if is_valid_label(asmlinesplit[1]) :
            lbl_name.append(asmlinesplit[1])
        else :
            print("Error: invalid label. Use only a-z, 0-9 and underscore, don't start with a number")
            print(full_source[linenum])
            sys.exit()
        lbl_line.append(asmlinesplit[0])
        # add -1 as marker for 'not initialized'
        lbl_value.append(-1)

    elif asmlinesplit[1] in named_args : 
        print("Error! Do not use reserved names as a label")
        print(full_source[linenum])
        sys.exit()

    if asmlinesplit[2] in mnemonics:
        while len(asmlinesplit) < 5:
            asmlinesplit.append('')
        asmlinesplit.extend([''] + [''] + [''] + [''] + [''])
    code.append(asmlinesplit)


# ---  Step 3 : assemble ---
# ##########################

for linenum, line in enumerate(code):
    if line[C_MNE] in mnemonics:
        add_to_code()
    elif line[C_MNE] in directives:
        exec_directive()
    else:
        print('Error: Mnemonic or directive expected.')
        print('See "' + listing_name + '" at line '  + str(line[C_LNUM]))
        print(full_source[line[C_LNUM] - 1])
        sys.exit(1)


# ---  Step 4 : link ---
# ######################

# replace all target labels with their value in hex
for linenum, line in enumerate(code):
    if line[C_MNE] not in directives :
        if (line[C_OLT] !='') and (line[C_OPCLO] in lbl_name) :
            code[linenum][C_OPCLO] = '0x%04X' % (lbl_value[lbl_name.index(line[C_OPCLO])])
        if line[C_ARG] in lbl_name :
            code[linenum][C_ARG] = '0x%04X' % (lbl_value[lbl_name.index(line[C_ARG])])
    elif line[C_MNE] == 'dw_e' :
        for wordnum, word in enumerate(line[C_ARG2:]) :
            if word in lbl_name :
                code[linenum][C_ARG2 + wordnum] = '0x%04X' % (lbl_value[lbl_name.index(word)])
    elif line[C_MNE] == 'res_e' :
        if line[C_ARG2] in lbl_name :
            code[linenum][C_ARG2] = '0x%04X' % (lbl_value[lbl_name.index(line[C_ARG2])])

for linenum, line in enumerate(code):
    if line[C_MNE] not in directives :
        if line[C_OLT] == '#U8' :
            u8temp = getnum(line[C_OPCLO])
            if u8temp > 255 :
                print('Error: Argument too big, must be 0 .. 255')
                print('See "' + listing_name + '" at line '  + str(line[C_LNUM]))
                print(full_source[line[C_LNUM] - 1])
                sys.exit(1)
            code[linenum][C_OPC] = '0x%04X' % (getnum(line[C_OPC]) + getnum(line[C_OPCLO]))
        if line[C_OLT] == '#S8' :
            targetaddr = getnum(line[C_OPCLO])
            curraddr = getnum(line[C_ADDR])
            offset = targetaddr - curraddr - 1
            if (offset > 128) or (offset < -127) :
                print('Error: Destination out of reach (-127 .. +128)')
                print('See "' + listing_name + '" at line '  + str(line[C_LNUM]))
                print(full_source[line[C_LNUM] - 1])
                sys.exit(1)
            if offset < 0 :
                offset = 256 + offset
            code[linenum][C_OPC] = '0x%04X' % (getnum(line[C_OPC]) + offset)


# ---  Step 5 : create final listing  ---
# #######################################

# add the hex listing to 'full_source' and overwrite listing file 
codelinenum = 0

for linenum, line in enumerate(full_source) :
    if code[codelinenum][C_LNUM] == linenum + 1:
        if code[codelinenum][C_MNE] not in directives : 
            temp = code[codelinenum][C_ADDR] + '  '
            temp = temp + code[codelinenum][C_OPC] + '  '
            if code[codelinenum][C_ARG] == '' :
                temp = temp + '        '
            else :
                temp = temp + code[codelinenum][C_ARG] + '   '
            full_source[linenum] = temp + full_source[linenum]
        elif code[codelinenum][C_MNE] == 'dw_e' :
            temp = '  '.join(code[codelinenum][C_ARG1:])
            full_source[linenum] = temp + ' | ' + full_source[linenum]
        else:
            full_source[linenum] = '                        ' + full_source[linenum]
        codelinenum += 1
        if codelinenum == len(code):
            break
    else:
        full_source[linenum] = '                        ' + full_source[linenum]

# append list of label/value pairs

labellisting = []

for x in range(len(lbl_line)):
    labellisting.append("Line " + str(lbl_line[x]) + "  ")
    labellisting.append(lbl_name[x] + ' ' + str(lbl_value[x]))
    labellisting.append(' | ' + str('0x%04X' % lbl_value[x]) + '\n')
with open(listing_name, 'w', encoding="utf-8") as listing:
    listing.writelines(full_source)
    listing.writelines('\n\nList of labels\n\n')
    listing.writelines(labellisting)


# ---  Step 6 : Generate output listings  ---
# #######################################m###

binlisting = []  # main.bin  Binary listing as init file for FPGA
ecmonlisting = []  # main.ecm  Hex listing in ecmon notation
load_addr : int = 0
memcount : int = 0
code_addr : int = 0
hexline = ''


# First: generate the .bin file that can be used for the initialization
# of a block ram via the FPGA configuration file. (Pseudo ROM)
#
# The files size must exactly match the BRAM size, so if there are gaps
# from skipping memory areas by using org_e or res_e directives these gaps
# are filled with zeros and included in the file
# The file length must be adjusted in the asm file via directives

# Although the resulting .bin file does not include any information where it is
# stored in the address space, we must keep track of the address information
# during the generation of the file to detect and handle gaps.  
# 

# Get the starting address by scanning for the first instruction/dw_e/res_e
for line in code:
    if (line[C_MNE] in mnemonics):
        memcount = getnum(line[C_ADDR])
        break
    elif (line[C_MNE] == 'dw_e'):
        memcount = getnum(line[C_ARG1])
        break
    elif (line[C_MNE] == 'res_e'):
        memcount = getnum(line[C_ARG1])
        break

# Now filter list 'code' for all instruction/dw_e/res_e entries
# since only these three types contribute to the data output
for line in code :

    if line[C_MNE] in mnemonics :
        code_addr = getnum(line[C_ADDR])
        while code_addr > memcount :
            binlisting.append('0000000000000000\n')
            memcount += 1
        hexline = line[C_OPC][2:]
        binlisting.append("{0:016b}".format(int(hexline, 16)) + '\n')
        memcount += 1
        if line[C_ARG] != '':
            hexline = line[C_ARG][2:]
            binlisting.append("{0:016b}".format(int(hexline, 16)) + '\n')
            memcount += 1
        continue
    elif line[C_MNE] == 'dw_e' :
        code_addr = getnum(line[C_ARG1])
        while code_addr > memcount :
            binlisting.append('0000000000000000\n')
            memcount += 1
        for hexline in line[C_ARG2:] :
            hexline = hexline[2:]
            binlisting.append("{0:016b}".format(int(hexline, 16)) + '\n')
            memcount += 1
        continue
    elif line[C_MNE] == 'res_e' :
        code_addr = getnum(line[C_ARG2])
        while code_addr > memcount :
            binlisting.append('0000000000000000\n')
            memcount += 1
        continue
    

# Second: generate a text file in the ECMON format
# i.e. Target address, '=', up to 8 words separated by space
# e.g. 8000=a100 807f a100 80d4 a100 80df a100 881b
# Empty sections (org_e/res_e) are not included

# Get the starting address again but this time ignore res_e
for line in code:
    if (line[C_MNE] in mnemonics):
        adjacentaddr = getnum(line[C_ADDR])
        break
    elif (line[C_MNE] == 'dw_e'):
        adjacentaddr = getnum(line[C_ARG1])
        break

# Now filter list 'code' for all instruction/dw_e entries
# since only these two types contribute to the data output

# Beginning from the start address gather up all contiguous code
# until the end of the list is reached or until a gap is found.
# Write this block to the file. If the end of code is not reached
# repeat the process.

block : list = []
block.append(adjacentaddr)

blocklist : list = [] 

for i in range(len(code)) :

    if (code[i][C_MNE] in mnemonics) :
        curraddr = getnum(code[i][C_ADDR])
        curropc =  code[i][C_OPC]
        currarg = [code[i][C_ARG]]
    elif (code[i][C_MNE] == 'dw_e') :
        curraddr = getnum(code[i][C_ARG1])
        curropc = ""
        currarg = code[i][C_ARG2:]
    else :
        continue   

    if curraddr != adjacentaddr :
        blocklist.append(block)
        block = [curraddr]
        adjacentaddr = curraddr
    oldblocklength = len(block)
    if curropc != "" :
        block.append(curropc)
    if currarg != [''] :
        block.extend(currarg)
    adjacentaddr += len(block) - oldblocklength

blocklist.append(block)

for block in blocklist :
    ecm_full_lines = int((len(block)-1) / 8)
    ecm_last_line =  int((len(block)-1) % 8)
    load_addr = block[0]
    offset : int = 1
    
    while ecm_full_lines > 0 :
        ecmonlisting.append('{:04x}'.format(load_addr))
        ecmonlisting.append('=')
        ecm_words=0
        while ecm_words < 7:
            ecmonlisting.append(block[offset + ecm_words][2:].lower())
            ecmonlisting.append(' ')
            ecm_words += 1
        ecmonlisting.append(block[offset + ecm_words][2:].lower())
        ecmonlisting.append('\n')
        offset += 8
        load_addr += 8
        ecm_full_lines -= 1

    if ecm_last_line > 0 :
        ecmonlisting.append('{:04x}'.format(load_addr))
        ecmonlisting.append('=')
        ecm_words=0
        while ecm_words < ecm_last_line - 1:
            ecmonlisting.append(block[offset + ecm_words][2:].lower())
            ecmonlisting.append(' ')
            ecm_words += 1
        ecmonlisting.append(block[offset + ecm_words][2:].lower())
        ecmonlisting.append('\n')
        

filename = sys.argv[1]
binlisting_name = Path(filename).stem + '.bin'
ecmlisting_name = Path(filename).stem + '.ecm'

with open(binlisting_name, 'w', encoding="utf-8") as listing:
    listing.writelines(binlisting)

with open(ecmlisting_name, 'w', encoding="utf-8") as listing:
    listing.writelines(ecmonlisting)

print('\n S U C C E S S \n')
print('Assembly complete without errors')
print('Generated the following files :')
print(' -  ', listing_name, '  (full listing)')
print(' -  ', binlisting_name, '  (bin data for FPGA memory)')
print(' -  ', ecmlisting_name, '  (hex data for upload with ECMON via terminal)')

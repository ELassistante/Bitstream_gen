'''
	    File name: bitstream_gen.py
	    Author: Clement DUBOS
	    Date created: 19/04/2022
	    Python Version: Python 3.10.4
	    Description: Encode instructions for the CGRA from usi pseudo asm
	'''

import io
import copy
from pickle import ADDITEMS

WALL = False

CGRA_N_COL = 4
CGRA_N_ROW = 4
PE_NBR = CGRA_N_ROW*CGRA_N_COL
SIZE_DEC_INSTR = 5
SIZE_EPFL_ASM = 6
rcs_nop_instr = ["ZEROS", "PREV", "NOP", "-", "PREV", "0"]
mux_instr = ["SRAM","RCL","RCR","RCT","RCB","R0","R1","R2","R3","ZEROS","-","ROUTA","Rout"]
reg_dest_instr = ['R0', 'R1', 'R2', 'R3', 'Rout']

def print_w(string) :
    if (WALL) :
        print(string)
    return

def time_lines (lines) :
    '''
        Reorganize the instructions in a timed order for each PE

        Parameter
        -----------------------------
        list of the lines(string) of bit_count_pseudo_assembly

        Return
        -----------------------------
        list of list of string    
    '''
    cnt = 0
    timed_lines = [[] for _ in range (PE_NBR)]
    for line in lines :
        if line == "\n" :
            cnt = 0
        else :
            if (line[-1] == '\n') :
                timed_lines[cnt].append(line[:-1])
            else :
                timed_lines[cnt].append(line[:])
            cnt += 1
    return timed_lines

def decode_instruction(instruction) :
    '''
        Separate operation and operators of instruction

        Parameter
        -----------------------------
        instruction (string)

        Return
        -----------------------------
        separated instruction (list of strings)    
    '''
    instr = ['' for _ in range(SIZE_DEC_INSTR)]
    case_list = ['Operation','OP1','OP2','OP3','END']
    case = case_list[0]
    rf_we = False
    once = False
    for char in instruction :
        if case == 'Operation' :
            if char != ' ' :
                instr[0] += char
            else :
                case = case_list[1]
        elif case == 'OP1' :
            if (char == ' ') or (char == ',') :
                if rf_we :
                    continue
                else :
                    case = case_list[2]
                    once = True
            elif (char == '-') or (char == '>'):
                rf_we = True
                continue
            elif rf_we :
                instr[3] += char
            else :
                instr[1] += char
        elif case == 'OP2' :
            if (char == ' ') or (char == ',') :
                if rf_we :
                    continue
                elif not(once) :
                    case = case_list[3]
                    once = True
                else :
                    continue
            elif (char == '>'):
                rf_we = True
                continue
            elif rf_we :
                instr[3] += char
            else :
                instr[2] += char
                once = False
        elif case == 'OP3' :
            if (char == ' ') or (char == ',') :
                if rf_we :
                    continue
                elif not(once) :
                    case = case_list[4]
                    once = True
                else :
                    continue
            elif (char == '-') or (char == '>'):
                rf_we = True
                continue
            else :
                instr[3] += char
        elif case == 'END' :
            return instr
    for i in range (SIZE_DEC_INSTR) :
        if (instr[i] == '') :
            instr[i] = '-'
    if (instr[0] == 'MV') :
        instr[0] = 'SADD'
        instr[1],instr[2] = instr[2],instr[1]
    elif (instr[0] == 'SUB') :
        instr[0] = 'SSUB'
    elif (instr[0] == 'ADD') :
        instr[0] = 'SADD'
    elif (instr[0] == 'MUL') :
        instr[0] = 'SMUL'
    elif (instr[0] == 'DIV') :
        instr[0] = 'SDIV'
    elif (instr[0] == 'SWD') :
        if (instr[1] == 'Rout') :
            instr[1] = 'R1'
            print_w('Rout considered as R1')
    if (instr[1] == '0') :
        instr[1] = 'ZEROS'
    elif (instr[1] == 'ROUTA') :
        instr[1] = 'R0'
    return instr

def translate_instructions (instr_usi) :
    '''
        Gives us the equivalent instruction in epfl assembly

        Parameter
        -----------------------------
        separated instruction (list of strings)   

        Return
        -----------------------------
        instruction (string)  
    '''


    instr_epfl = ['' for _ in range (SIZE_EPFL_ASM)]
    op = instr_usi[0]

    if op == 'NOP' :
        instr_epfl = rcs_nop_instr
    else :
        instr_epfl = [instr_usi[1],instr_usi[2] if (instr_usi[2] in mux_instr) else "IMM",op,instr_usi[3],'-',instr_usi[2] if not(instr_usi[2] in mux_instr) else "-"] #change the 0 in the future
        if (instr_epfl[3] not in reg_dest_instr) and (instr_epfl[3] != '-') :
            instr_epfl[3] = 'R3'
            print_w("absolute beq instruction not implemented yet :")
            print_w(instr_epfl)
        if (instr_epfl[0] == 'ROUTA') :
            instr_epfl[0] = 'R0'
            print_w("ROUTA considered as R0 :")     #not sure
            print_w(instr_epfl)
        elif (instr_epfl[0] not in mux_instr) :
            instr_epfl[0] = 'ZEROS'
            print_w("Warning mux_instr not in list :")
            print_w(instr_epfl)
        if (instr_epfl[3] == 'Rout') :
            instr_epfl[3] = 'R1'        # not sure about this but seems that there is only one out reg
            print_w("Rout considered as R1 :")
            print_w(instr_epfl)
    return instr_epfl

def translate_usi_asm(sched) :
    '''
        Translate usi pseudo-assembly to epfl cgra assembly

        Parameter
        -----------------------------
        schedule of the execution (list of list of string) in usi pseudo-assembly

        Return
        -----------------------------
        schedule of the execution (list of list of string) in epfl cgra assembly  
    '''
    new_sched = [[['' for _ in range(SIZE_EPFL_ASM)] for _ in range(len(sched[0]))] for _ in range(PE_NBR)]
    i = 0
    j = 0
    for pe in sched :
        for instruction in pe :
            instr  = decode_instruction(instruction)
 #           print(instr)
#            print(translate_instructions(instr))
            new_sched[i][j] = translate_instructions(instr)
            j += 1
            #print(new_sched[i][j] )
        j = 0
        i += 1

    return new_sched

def transpose_grid(usi_trans) :
    '''
        Transpose the PE grid because epfl doesn't use the same convention as usi

        Parameter
        -----------------------------
        Translated usi pseudo-assembly in epfl format (list of list of string)

        Return
        -----------------------------
        epfl format assembly (list of list of string)
    '''
    epfl_asm = copy.copy(usi_trans)
    epfl_asm[1] = usi_trans[4]
    epfl_asm[2] = usi_trans[8]
    epfl_asm[3] = usi_trans[12]
    epfl_asm[4] = usi_trans[1]
    epfl_asm[6] = usi_trans[9]
    epfl_asm[7] = usi_trans[13]
    epfl_asm[8] = usi_trans[2]
    epfl_asm[9] = usi_trans[6]
    epfl_asm[11] = usi_trans[14]
    epfl_asm[12] = usi_trans[3]
    epfl_asm[13] = usi_trans[7]
    epfl_asm[14] = usi_trans[11]
#    for pe in epfl_asm :
#        print(pe)
    return epfl_asm

def set_ker_conf_word(code) :
    '''
        Set the kernel configuration word

        Parameter
        -----------------------------
        the translated and reformated cgra asm instruction (list of list of string)

        Return
        -----------------------------
        the kernel configuration word, k, kernel start aderss
    '''
    col_used = [0,0,0,0]
    for i in range(PE_NBR) :
        for instr in code[i] :
            if instr != rcs_nop_instr :
                if (i <=3) :
                    col_used[0] = 1
                elif (i <=7) :
                    col_used[1] = 1
                elif (i <=11) :
                    col_used[2] = 1
                else :
                    col_used[3] = 1
    nbr_col = sum(col_used)
    ker_num_instr = len(code[0])
    ker_conf_w = get_bin(int(pow(2,nbr_col))-1,CGRA_N_COL) +\
                                get_bin(ker_start_add, CGRA_IMEM_NL_LOG2) +\
                                get_bin(ker_num_instr-1, RCS_NUM_CREG_LOG2)
    # Used for multi-column kernels
    k = ker_num_instr
    return ker_conf_w,nbr_col,k

def create_rcs_instructions(start_add,rcs_instructions,epfl_ASM) :
    for j in range(len(epfl_ASM)) :
        for i in range(len(epfl_ASM[0])) :
            rcs_instructions[j][start_add+i] = epfl_ASM[j][i]
    return rcs_instructions

'''--------------------------------
CODE
--------------------------------'''

usi_ASM_file = open("bit_count_pseudo_assembly","r")
usi_ASM = usi_ASM_file.readlines()
#print(usi_ASM)
usi_ASM_timed = time_lines(usi_ASM)
#print(usi_ASM_timed)
usi_translated = translate_usi_asm(usi_ASM_timed)
epfl_ASM = transpose_grid(usi_translated)
'''for pe in epfl_ASM :
    print('\n')
    for i in range(len(pe)) :
        print(pe[i])'''
start_add = ker_start_add           # Save current start address
ker_conf_words[ker_next_id],nbr_col,k = set_ker_conf_word(epfl_ASM)
# Update start address for next kernel
ker_start_add = ker_start_add + k*nbr_col
ker_next_id = ker_next_id+1         #update ID for next kernel
#print(len(rcs_instructions))
#print(len(rcs_instructions[0]))
rcs_instructions = create_rcs_instructions(start_add,rcs_instructions,epfl_ASM)

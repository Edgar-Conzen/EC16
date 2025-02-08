# EC16
The EC16 is a 16-bit soft microprocessor for FPGAs written in VHDL.

 <img src="/Doc/EC16_Logo.jpg" width="400" />
 
# Some basic characteristics:
- 16-bit data width
- 16-bit address space for external memory (code, data and I/O)
- 256 word internal memory (registers, stack, scratch pad memory)
- 50 instructions
  * instruction length: mostly single word, only 4 instructions with two words
  * speed: 18 one-cycle, 15 two-cycle, 9 three-cycle, 8 one/two-cycle (branch)
- 4 maskable prioritized interrupts

The EC16 is implemented as an open source Lattice Radiant Project [EC16_on_ICE](https://github.com/Edgar-Conzen/EC16_on_ICE) for the [ICY40 board](https://github.com/Edgar-Conzen/ICY40), 
running at 20 MHz and using only about 21% of the ICE40UP5K FPGAs logic resources while already including peripherals like COM-Port and I2C Master.

  <img src="/Doc/ICY40_EC16_writes_text_on_display.jpg" width="500" />

 # Downloads
 - [Processor Handbook](https://raw.github.com/Edgar-Conzen/EC16/main/Download/EC16_ISA_V1.0.pdf)
 - [EC16ASM syntax highlighting for Notepad++](https://raw.github.com/Edgar-Conzen/EC16/main/Download/EC16_ASM_Syntax_for_NotepadPP.xml)
 - [EC16 Assembler as Python Program](https://raw.github.com/Edgar-Conzen/EC16/main/Download/ec16asm.py)

# Further Information
See the [EC16 Wiki](https://github.com/Edgar-Conzen/EC16/wiki)

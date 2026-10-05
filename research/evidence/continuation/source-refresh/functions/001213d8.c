
int FUN_001213d8(uint param_1)

{
  return *(int *)(&DAT_00233080 + (param_1 >> 0x14 & 0xf) * 0x114) + (param_1 & 0xffff) * 0x58;
}


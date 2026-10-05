
void FUN_0018de60(int param_1)

{
  int iVar1;
  float fVar2;
  
  fVar2 = FLOAT_00290a80;
  iVar1 = *(int *)(param_1 + 4);
  *(float *)(iVar1 + 0xfc) = *(float *)(iVar1 + 0xfc) + FLOAT_00290a80;
  *(float *)(iVar1 + 0x104) = *(float *)(iVar1 + 0x104) + fVar2;
  *(float *)(iVar1 + 0x10c) = *(float *)(iVar1 + 0x10c) + fVar2;
  *(float *)(iVar1 + 0x114) = *(float *)(iVar1 + 0x114) + fVar2;
  *(float *)(iVar1 + 0x11c) = *(float *)(iVar1 + 0x11c) + fVar2;
  return;
}


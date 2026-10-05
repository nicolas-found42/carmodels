
int FUN_00121cd0(float param_1,int param_2)

{
  byte bVar1;
  float *pfVar2;
  int iVar3;
  int iVar4;
  float fVar5;
  
  if (iRam0028f0ec != 0) {
    param_1 = param_1 * *(float *)(iRam0028f0ec + 0x20);
  }
  iVar4 = 1;
  if (*(byte *)(param_2 + 0x12) < 2) {
    bVar1 = *(byte *)(param_2 + 0x11);
LAB_00121d8c:
    iVar4 = bVar1 - 1;
  }
  else {
    pfVar2 = (float *)(*(int *)(param_2 + 0x4c) + 4);
    fVar5 = *pfVar2;
    while (pfVar2 = pfVar2 + 1, fVar5 < param_1) {
      iVar4 = iVar4 + 1;
      if ((int)(uint)*(byte *)(param_2 + 0x12) <= iVar4) {
        bVar1 = *(byte *)(param_2 + 0x11);
        goto LAB_00121d8c;
      }
      fVar5 = *pfVar2;
    }
    bVar1 = *(byte *)(param_2 + 0x11);
    iVar4 = iVar4 + iRam0028f130 + -1;
    iVar3 = bVar1 - 1;
    if (iVar3 <= iVar4) {
      iVar4 = bVar1 - 2;
      if (bVar1 < 3) {
        iVar4 = iVar3;
      }
      return iVar4;
    }
    if ((iVar4 < iRam0028f12c) && (iVar4 = iRam0028f12c, iVar3 <= iRam0028f12c)) {
      iVar4 = bVar1 - 2;
      if (bVar1 < 3) {
        iVar4 = 0;
      }
      return iVar4;
    }
  }
  return iVar4;
}


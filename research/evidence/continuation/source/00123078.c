
void FUN_00123078(int param_1)

{
  int iVar1;
  uint uVar2;
  int iVar3;
  ushort *puVar4;
  int iVar5;
  
  iVar5 = 0;
  if (*(char *)(param_1 + 4) != '\0') {
    iVar3 = 0;
    do {
      iVar5 = iVar5 + 1;
      iVar1 = iVar3 + *(int *)(param_1 + 0x28);
      *(uint *)(iVar1 + 4) = *(uint *)(iVar1 + 4) & 0xfffeffff;
      iVar3 = iVar3 + 0x2c;
    } while (iVar5 < (int)(uint)*(byte *)(param_1 + 4));
  }
  uVar2 = *(uint *)(param_1 + 4);
  iVar5 = 0;
  if ((uVar2 >> 8 & 0x3f) != 0) {
    iVar3 = 0;
    do {
      iVar5 = iVar5 + 1;
      iVar1 = iVar3 + *(int *)(param_1 + 0x28);
      *(uint *)(iVar1 + 4) = *(uint *)(iVar1 + 4) | 0x10000;
      uVar2 = *(uint *)(param_1 + 4);
      iVar3 = iVar3 + 0x2c;
    } while (iVar5 < (int)(uVar2 >> 8 & 0x3f));
  }
  iVar5 = 0;
  if ((uVar2 >> 8 & 0x3f) != 0) {
    puVar4 = *(ushort **)(param_1 + 8);
    do {
      iVar5 = iVar5 + 1;
      (&DAT_002cb310)[*puVar4] = (&DAT_002cb310)[*puVar4] + 1;
      puVar4 = puVar4 + 2;
    } while (iVar5 < (int)(*(uint *)(param_1 + 4) >> 8 & 0x3f));
  }
  iVar5 = 0;
  if (*(char *)(param_1 + 4) != '\0') {
    iVar1 = 0;
    iVar3 = *(int *)(param_1 + 0x28);
    while( true ) {
      iVar5 = iVar5 + 1;
      iVar3 = iVar3 + iVar1;
      iVar1 = iVar1 + 0x2c;
      FUN_00123078(iVar3);
      if ((int)(uint)*(byte *)(param_1 + 4) <= iVar5) break;
      iVar3 = *(int *)(param_1 + 0x28);
    }
  }
  return;
}


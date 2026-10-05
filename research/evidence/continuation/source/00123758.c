
void FUN_00123758(int param_1)

{
  ushort uVar1;
  int iVar2;
  undefined2 *puVar3;
  int iVar4;
  int iVar5;
  
  iVar5 = 0;
  if ((*(uint *)(param_1 + 4) >> 8 & 0x3f) != 0) {
    iVar4 = *(int *)(param_1 + 8);
    while( true ) {
      iVar2 = iVar5 * 4;
      iVar5 = iVar5 + 1;
      puVar3 = (undefined2 *)(iVar2 + iVar4);
      uVar1 = puVar3[1];
      FUN_00123820(*puVar3,*(int *)(param_1 + 0x28) + ((uint)uVar1 * 0xc - (uint)uVar1) * 4);
      if ((int)(*(uint *)(param_1 + 4) >> 8 & 0x3f) <= iVar5) break;
      iVar4 = *(int *)(param_1 + 8);
    }
  }
  iVar5 = 0;
  if (*(char *)(param_1 + 4) != '\0') {
    iVar2 = 0;
    iVar4 = *(int *)(param_1 + 0x28);
    while( true ) {
      iVar5 = iVar5 + 1;
      iVar4 = iVar4 + iVar2;
      iVar2 = iVar2 + 0x2c;
      FUN_00123758(iVar4);
      if ((int)(uint)*(byte *)(param_1 + 4) <= iVar5) break;
      iVar4 = *(int *)(param_1 + 0x28);
    }
  }
  return;
}


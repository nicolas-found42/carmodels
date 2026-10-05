
undefined4 FUN_001231c0(int *param_1)

{
  ushort uVar1;
  int iVar2;
  undefined4 uVar3;
  uint *puVar4;
  int iVar5;
  int iVar6;
  
  iVar6 = 0;
  iGpffffaa1c = param_1[2];
  uVar1 = *(ushort *)(param_1 + 3);
  iVar2 = FUN_001213d8(*(undefined4 *)(*param_1 + 4));
  iVar5 = 0;
  puVar4 = *(uint **)(iVar2 + 0x34);
  if (*(byte *)(iVar2 + 0x15) != 0) {
    do {
      if (*puVar4 == (uint)uVar1) {
        if (iGpffffaa1c < (int)puVar4[1]) {
          iVar6 = *(int *)(iGpffffaa1c * 4 + puVar4[2]);
        }
        break;
      }
      iVar5 = iVar5 + 1;
      puVar4 = puVar4 + 3;
    } while (iVar5 < (int)(uint)*(byte *)(iVar2 + 0x15));
  }
  if (iVar6 == 0) {
    param_1[4] = 0;
    uVar3 = 2;
  }
  else {
    iVar2 = FUN_00123450(*(undefined4 *)(*param_1 + 4),iVar6);
    param_1[4] = iVar6;
    iVar5 = *(int *)(iVar6 + 0x18);
    param_1[1] = iVar2;
    uVar3 = 1;
    param_1[5] = iVar5;
    param_1[6] = *(int *)(iVar6 + 0x1c);
    param_1[7] = *(int *)(iVar6 + 0x20);
  }
  return uVar3;
}


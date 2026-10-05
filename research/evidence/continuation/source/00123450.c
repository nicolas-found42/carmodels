
int FUN_00123450(undefined8 param_1,int param_2,int param_3)

{
  uint uVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  uint *puVar5;
  int *piVar6;
  int iVar7;
  int aiStack_a4 [33];
  
  piVar6 = aiStack_a4 + 1;
  iVar2 = FUN_001213d8();
  iVar7 = 0;
  for (; param_2 != 0; param_2 = *(int *)(param_2 + 0x24)) {
    *piVar6 = param_2;
    piVar6 = piVar6 + 1;
    iVar7 = iVar7 + 1;
  }
  iVar3 = (aiStack_a4[iVar7] - *(int *)(iVar2 + 0x54) >> 2) * -0x45d1745d;
  iVar4 = *(int *)(param_3 + 0x6c);
  if (0 < iVar3) {
    puVar5 = (uint *)(*(int *)(iVar2 + 0x54) + 4);
    do {
      uVar1 = *puVar5;
      puVar5 = puVar5 + 0xb;
      iVar2 = iVar4 + 0x10;
      iVar3 = iVar3 + -1;
      iVar4 = iVar4 + 0x40;
      if ((uVar1 & 0x10000) == 0) {
        iVar4 = iVar2;
      }
    } while (iVar3 != 0);
  }
  iVar3 = iVar7 + -2;
  iVar2 = aiStack_a4[iVar7];
  if (-1 < iVar3) {
    piVar6 = aiStack_a4 + iVar7 + -1;
    do {
      iVar7 = (*piVar6 - *(int *)(iVar2 + 0x28) >> 2) * -0x45d1745d;
      iVar4 = *(int *)(iVar4 + 4);
      if (0 < iVar7) {
        puVar5 = (uint *)(*(int *)(iVar2 + 0x28) + 4);
        do {
          uVar1 = *puVar5;
          puVar5 = puVar5 + 0xb;
          iVar2 = iVar4 + 0x10;
          iVar7 = iVar7 + -1;
          iVar4 = iVar4 + 0x40;
          if ((uVar1 & 0x10000) == 0) {
            iVar4 = iVar2;
          }
        } while (iVar7 != 0);
      }
      iVar3 = iVar3 + -1;
      iVar2 = *piVar6;
      piVar6 = piVar6 + -1;
    } while (-1 < iVar3);
  }
  return iVar4;
}


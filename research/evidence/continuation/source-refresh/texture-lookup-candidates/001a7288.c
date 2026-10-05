
undefined8
candidate_ee_001a7288(undefined8 param_1,undefined4 param_2,undefined4 param_3,undefined8 param_4)

{
  undefined4 uVar1;
  int iVar2;
  int iVar3;
  uint uVar4;
  undefined4 uVar5;
  undefined4 *puVar6;
  int iVar7;
  int iVar8;
  undefined8 uVar9;
  undefined8 uVar10;
  int *piVar11;
  undefined1 auStack_250 [256];
  undefined1 auStack_150 [256];
  
  iVar7 = *(int *)((int)param_1 + 4);
  iVar8 = *(int *)(iVar7 + 0x23fc);
  uVar1 = *(undefined4 *)(iVar7 + 0x48);
  uVar4 = FUN_001a8768();
  if (uVar4 == 0) {
    iVar3 = *(int *)(iVar8 + 8);
    iVar7 = 0;
    while (iVar2 = iVar3, iVar2 != 0) {
      iVar7 = iVar2;
      iVar3 = *(int *)(iVar2 + 0xc);
    }
    uVar9 = FUN_00118cd0(iVar8,0);
    FUN_00118d80(uVar9,iVar8,iVar7);
    uVar4 = (int)uVar9 + 0x1fU & 0xfffffff0;
    FUN_0020c7fc(uVar4,0,0x54);
    FUN_00101730(auStack_150,0x100,0x262a50,uVar1,param_4);
    uVar5 = FUN_00118bc8(auStack_150,0xc,0,1);
    *(undefined4 *)(uVar4 + 0x48) = uVar5;
    puVar6 = (undefined4 *)FUN_0010d020(4);
    *(undefined4 **)(uVar4 + 0x50) = puVar6;
    *puVar6 = 0;
    FUN_00101730(auStack_250,0x100,0x262a60,uVar1,param_4);
    iVar7 = FUN_00118bc8(auStack_250,0x84,0,1);
    piVar11 = *(int **)(uVar4 + 0x50);
    *(undefined4 *)(uVar4 + 4) = param_2;
    *piVar11 = iVar7;
  }
  else {
    piVar11 = *(int **)(uVar4 + 0x50);
  }
  iVar7 = *(int *)(*(int *)(uVar4 + 0x48) + 8);
  if (iVar7 == 0) {
    iVar7 = *piVar11;
  }
  else {
    for (iVar7 = *(int *)(iVar7 + 0xc); iVar7 != 0; iVar7 = *(int *)(iVar7 + 0xc)) {
    }
    iVar7 = *piVar11;
  }
  if (*(int *)(iVar7 + 8) != 0) {
    for (iVar7 = *(int *)(*(int *)(iVar7 + 8) + 0xc); iVar7 != 0; iVar7 = *(int *)(iVar7 + 0xc)) {
    }
  }
  uVar9 = FUN_001af820(3,4,7,param_1,2);
  iVar8 = FUN_001af820(9,4,2,uVar9,2);
  iVar7 = *(int *)((int)uVar9 + 4);
  iVar8 = *(int *)(iVar8 + 4);
  *(ulong *)(iVar7 + 0xf0) = *(ulong *)(iVar7 + 0xf0) & 0xffffffffffffbf97 | 0x200;
  *(undefined4 *)(iVar7 + 0x120) = 2;
  *(undefined4 *)(iVar7 + 0x184) = 0x42800000;
  *(undefined4 *)(iVar7 + 0x150) = 1;
  *(undefined4 *)(iVar7 + 0xcc) = 1;
  *(undefined4 *)(iVar7 + 0x14c) = 1;
  *(undefined4 *)(iVar7 + 400) = 0x42800000;
  *(undefined4 *)(iVar7 + 0x194) = 0x42800000;
  *(undefined4 *)(iVar8 + 0xd8) = 3;
  *(undefined4 *)(iVar8 + 0xec) = 3;
  *(undefined4 *)(iVar8 + 0xf0) = 3;
  *(undefined4 *)(iVar8 + 0xf4) = 3;
  *(undefined4 *)(iVar8 + 0xdc) = 1;
  *(undefined4 *)(iVar7 + 0xd0) = 4;
  *(undefined4 *)(iVar7 + 0xc4) = param_3;
  *(undefined4 *)(iVar7 + 0xc0) = param_2;
  *(undefined4 *)(iVar7 + 0x264) = 0;
  *(undefined4 *)(iVar7 + 200) = 0;
  *(undefined4 *)(iVar7 + 0xf8) = 0;
  *(undefined4 *)(iVar7 + 0x140) = 3;
  *(undefined4 *)(iVar7 + 0x144) = 3;
  *(undefined4 *)(iVar7 + 0x148) = 3;
  *(undefined4 *)(iVar7 + 0x134) = 3;
  *(undefined4 *)(iVar7 + 0x138) = 3;
  *(undefined4 *)(iVar7 + 0x13c) = 3;
  uVar10 = FUN_00118cd0(*(undefined4 *)(uVar4 + 0x48),0);
  puVar6 = (undefined4 *)((int)uVar10 + 0x1fU & 0xfffffff0);
  FUN_00118d80(uVar10,*(undefined4 *)(uVar4 + 0x48),0);
  FUN_0020c7fc(puVar6,0,0xc);
  puVar6[2] = 0;
  puVar6[1] = param_3;
  *puVar6 = param_2;
  uVar10 = FUN_00118cd0(*(undefined4 *)(uVar4 + 0x48),0);
  FUN_00118d80(uVar10,**(undefined4 **)(uVar4 + 0x50),0);
  *(undefined4 *)((int)uVar10 + 0x1fU & 0xfffffff0) = param_2;
  return uVar9;
}


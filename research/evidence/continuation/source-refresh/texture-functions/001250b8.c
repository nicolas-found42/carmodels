
undefined4 FUN_001250b8(ulong param_1,undefined8 param_2)

{
  int iVar1;
  uint uVar2;
  char *pcVar3;
  undefined4 uVar4;
  long lVar5;
  int iVar6;
  uint *puVar7;
  ulong uVar8;
  uint uVar9;
  
  iVar1 = FUN_0021b6e0();
  uVar2 = FUN_0020e10c(param_2);
  iVar6 = 0;
  uVar9 = uVar2;
  if (0 < (int)uVar2) {
    do {
      pcVar3 = (char *)((int)param_2 + iVar6);
      iVar6 = iVar6 + 1;
      uVar9 = (uVar9 + (int)*pcVar3) * 2;
    } while (iVar6 < (int)uVar2);
  }
  puVar7 = *(uint **)((uVar9 & 0xff) * 4 + *(int *)(iVar1 + 0x10c));
  if (puVar7 == (uint *)0x0) {
    uVar8 = 0xffffffffffffffff;
  }
  else {
    uVar2 = *puVar7;
    while( true ) {
      if (uVar2 == uVar9) {
        lVar5 = FUN_0020db20(*(undefined4 *)(puVar7[1] * 4 + *(int *)(iVar1 + 0x104)),param_2);
        if (lVar5 == 0) {
          uVar8 = param_1 & 0xfffffffffff00000 | 0x40000 | (ulong)(ushort)puVar7[1];
          goto LAB_001251ac;
        }
        puVar7 = (uint *)puVar7[2];
      }
      else {
        puVar7 = (uint *)puVar7[2];
      }
      if (puVar7 == (uint *)0x0) break;
      uVar2 = *puVar7;
    }
    uVar8 = 0xffffffffffffffff;
  }
LAB_001251ac:
  if (uVar8 == 0xffffffffffffffff) {
    uVar4 = 0;
  }
  else {
    iVar1 = FUN_0021b6e0(uVar8);
    uVar4 = *(undefined4 *)(((uint)uVar8 & 0xffff) * 4 + *(int *)(iVar1 + 0xec));
  }
  return uVar4;
}


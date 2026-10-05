
ulong FUN_00124f58(ulong param_1,undefined8 param_2)

{
  int iVar1;
  uint uVar2;
  char *pcVar3;
  long lVar4;
  int iVar5;
  uint *puVar6;
  uint uVar7;
  
  iVar1 = FUN_0021b6e0();
  uVar2 = FUN_0020e10c(param_2);
  iVar5 = 0;
  uVar7 = uVar2;
  if (0 < (int)uVar2) {
    do {
      pcVar3 = (char *)((int)param_2 + iVar5);
      iVar5 = iVar5 + 1;
      uVar7 = (uVar7 + (int)*pcVar3) * 2;
    } while (iVar5 < (int)uVar2);
  }
  puVar6 = *(uint **)((uVar7 & 0xff) * 4 + *(int *)(iVar1 + 0x10c));
  if (puVar6 != (uint *)0x0) {
    uVar2 = *puVar6;
    while( true ) {
      if (uVar2 == uVar7) {
        lVar4 = FUN_0020db20(*(undefined4 *)(puVar6[1] * 4 + *(int *)(iVar1 + 0x104)),param_2);
        if (lVar4 == 0) {
          return param_1 & 0xfffffffffff00000 | 0x40000 | (ulong)(ushort)puVar6[1];
        }
        puVar6 = (uint *)puVar6[2];
      }
      else {
        puVar6 = (uint *)puVar6[2];
      }
      if (puVar6 == (uint *)0x0) break;
      uVar2 = *puVar6;
    }
  }
  return 0xffffffffffffffff;
}


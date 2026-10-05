
uint FUN_00124e98(uint param_1,undefined8 param_2)

{
  int iVar1;
  long lVar2;
  int iVar3;
  uint uVar4;
  
  iVar1 = FUN_0021b6e0();
  uVar4 = 0;
  if (*(int *)(iVar1 + 0xb8) < 1) {
LAB_00124f30:
    uVar4 = 0xffffffff;
  }
  else {
    iVar3 = *(int *)(iVar1 + 0x8c);
    while( true ) {
      lVar2 = FUN_0020db20(param_2,*(undefined4 *)(uVar4 * 4 + iVar3));
      if (lVar2 == 0) break;
      uVar4 = uVar4 + 1;
      if (*(int *)(iVar1 + 0xb8) <= (int)uVar4) goto LAB_00124f30;
      iVar3 = *(int *)(iVar1 + 0x8c);
    }
    uVar4 = param_1 & 0xfff00000 | 0x50000 | uVar4 & 0xffff;
  }
  return uVar4;
}


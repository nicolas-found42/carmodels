
undefined8
FUN_0019bfe0(undefined8 param_1,undefined4 param_2,undefined8 param_3,undefined1 *param_4,
            ulong param_5)

{
  long lVar1;
  long lVar2;
  undefined8 uVar3;
  int iVar4;
  undefined1 auStack_80 [32];
  undefined4 uStack_60;
  int iStack_5c;
  int iStack_58;
  undefined4 uStack_54;
  
  FUN_00101730(auStack_80,0x20,0x28ff60,param_3);
  lVar1 = FUN_00124e98(param_1,auStack_80);
  iVar4 = 0;
  if (lVar1 != -1) {
    iStack_58 = 0;
    while (iVar4 = iStack_58, uStack_60 = param_2, uStack_54 = (int)lVar1,
          lVar2 = FUN_001231c0(&uStack_60), lVar2 == 1) {
      iStack_58 = iVar4 + 1;
    }
  }
  uVar3 = 0;
  if (0 < iVar4) {
    *param_4 = (char)iVar4;
    uVar3 = FUN_0010d020(iVar4 << 2);
    iStack_58 = 0;
    while( true ) {
      iVar4 = iStack_58;
      uStack_60 = param_2;
      uStack_54 = (int)lVar1;
      lVar2 = FUN_001231c0(&uStack_60);
      iStack_58 = iVar4 + 1;
      if (lVar2 != 1) break;
      *(int *)(iVar4 * 4 + (int)uVar3) = iStack_5c;
      *(ulong *)(iStack_5c + 8) = *(ulong *)(iStack_5c + 8) & 0xfffffffffffffffe | param_5 & 1;
    }
  }
  return uVar3;
}


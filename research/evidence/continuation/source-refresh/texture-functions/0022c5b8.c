
void FUN_0022c5b8(undefined8 param_1,int param_2)

{
  undefined8 uVar1;
  int iVar2;
  int iVar3;
  
  if (1 < param_2) {
    uVar1 = FUN_0010d020(param_2 << 2);
    iVar3 = 0;
    if (0 < param_2) {
      do {
        iVar2 = iVar3 * 4;
        iVar3 = iVar3 + 1;
        *(uint *)(iVar2 + (int)uVar1) = (uint)*(ushort *)(*(int *)(iVar2 + (int)param_1) + 0x30);
      } while (iVar3 < param_2);
    }
    FUN_00127598(param_1,uVar1,0,param_2 + -1);
    FUN_0010d100(uVar1);
    return;
  }
  return;
}


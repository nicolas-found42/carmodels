
void FUN_001056b0(long param_1)

{
  int iVar1;
  int iVar2;
  long lVar3;
  
  iVar1 = DAT_0029060c;
  if (DAT_0029060c != 0) {
    if (*(int *)(DAT_0029060c + 0x104) == 0) {
      if (param_1 != 0) {
        FUN_001057f0(DAT_0029060c);
      }
    }
    else {
      if (*(int *)(DAT_0029060c + 0x108) == 0) {
        lVar3 = FUN_0010d538();
        if (lVar3 == 0) {
          iVar2 = *(int *)(iVar1 + 0x108);
        }
        else {
          FUN_0010d560();
          *(undefined4 *)(iVar1 + 0x108) = 1;
          iVar2 = *(int *)(iVar1 + 0x108);
        }
        if (iVar2 == 0) {
          return;
        }
        iVar2 = *(int *)(iVar1 + 0x10c);
      }
      else {
        iVar2 = *(int *)(DAT_0029060c + 0x10c);
      }
      if (iVar2 != 0) {
        *(undefined4 *)(iVar1 + 0x100) = 0;
      }
      iVar2 = *(int *)(iVar1 + 0x11c);
      DAT_0029060c = 0;
      if (*(int *)(iVar1 + 0x118) != 0) {
        *(int *)(*(int *)(iVar1 + 0x118) + 0x11c) = iVar2;
        DAT_0029060c = *(int *)(iVar1 + 0x118);
        iVar2 = *(int *)(iVar1 + 0x11c);
      }
      if (iVar2 != 0) {
        *(int *)(iVar2 + 0x118) = DAT_0029060c;
        DAT_0029060c = *(int *)(iVar1 + 0x118);
      }
      if (DAT_00290610 == iVar1) {
        DAT_00290610 = DAT_0029060c;
      }
      *(undefined4 *)(iVar1 + 0x11c) = 0;
      *(undefined4 *)(iVar1 + 0x118) = 0;
    }
  }
  return;
}


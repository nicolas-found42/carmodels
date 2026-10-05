
void FUN_0019a7b8(float param_1,undefined4 param_2,undefined4 param_3,int param_4,int param_5,
                 ulong param_6)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  int *piVar5;
  int iVar6;
  int iVar7;
  int *piVar8;
  int iVar9;
  int *piVar10;
  long lVar11;
  float fVar12;
  undefined1 in_vf0 [16];
  undefined1 auVar13 [16];
  undefined1 auVar14 [16];
  
  iVar3 = iRam0028ff58;
  lVar11 = 0;
  iVar1 = *(int *)(param_4 + 4);
  iVar7 = param_5 * 0x1c + 0x150;
  if ('\0' < *(char *)(iVar1 + iVar7 + 1)) {
    iVar9 = iVar1 + 8;
    piVar10 = (int *)(iVar9 + iVar7);
    auVar14 = _qmtc2(0);
    iVar7 = 0;
    do {
      iVar4 = *(int *)(iVar7 + *(int *)(param_5 * 0x1c + iVar9 + 0x150));
      *(undefined4 *)(iVar4 + 0x28) = 0;
      fVar12 = *(float *)(iVar4 + 0x24) + param_1;
      *(float *)(iVar4 + 0x24) = fVar12;
      while (3.1415925 < fVar12) {
        iVar4 = *(int *)(iVar7 + *(int *)(param_5 * 0x1c + iVar9 + 0x150));
        fVar12 = *(float *)(iVar4 + 0x24) - 6.283185;
        *(float *)(iVar4 + 0x24) = fVar12;
      }
      fVar12 = *(float *)(*(int *)(iVar7 + *piVar10) + 0x24);
      while (fVar12 < -3.1415925) {
        iVar4 = *(int *)(iVar7 + *(int *)(param_5 * 0x1c + iVar9 + 0x150));
        fVar12 = *(float *)(iVar4 + 0x24) + 6.283185;
        *(float *)(iVar4 + 0x24) = fVar12;
      }
      iVar6 = param_5 * 0x1c + 0x160;
      iVar4 = *(int *)(iVar7 + *piVar10);
      piVar8 = (int *)(iVar7 + *(int *)(iVar1 + iVar6));
      iVar2 = *piVar8;
      _lqc2(*(undefined1 (*) [16])(iVar4 + 0x10));
      auVar13 = _vaddbc(in_vf0,auVar14);
      auVar13 = _sqc2(auVar13);
      *(undefined1 (*) [16])(iVar4 + 0x10) = auVar13;
      *(undefined4 *)(iVar4 + 0x2c) = param_3;
      if (iVar2 != 0) {
        *(ulong *)(iVar2 + 8) = *(ulong *)(iVar2 + 8) & 0xfffffffffffffffe | ~param_6 & 1;
      }
      piVar5 = (int *)(iVar7 + *(int *)(iVar1 + 4 + iVar6));
      iVar4 = *piVar5;
      if (iVar4 != 0) {
        *(ulong *)(iVar4 + 8) = *(ulong *)(iVar4 + 8) & 0xfffffffffffffffe | param_6 & 1;
      }
      if (iVar3 != 0) {
        iVar4 = *piVar8;
        if (iVar4 == 0) {
          iVar4 = *piVar5;
        }
        else {
          *(ulong *)(iVar4 + 8) = *(ulong *)(iVar4 + 8) & 0xfffffffffffffffe;
          iVar4 = *piVar5;
        }
        if (iVar4 != 0) {
          *(ulong *)(iVar4 + 8) = *(ulong *)(iVar4 + 8) | 1;
        }
      }
      lVar11 = (long)((int)lVar11 + 1);
      iVar7 = iVar7 + 4;
    } while (lVar11 < *(char *)(param_5 * 0x1c + iVar1 + 0x151));
  }
  return;
}


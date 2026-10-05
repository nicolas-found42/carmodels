
void FUN_0019a7b8(float param_1,undefined4 param_2,undefined4 param_3,int param_4,int param_5,
                 ulong param_6)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int *piVar4;
  int iVar5;
  int iVar6;
  int *piVar7;
  int iVar8;
  int *piVar9;
  long lVar10;
  float fVar11;
  undefined1 in_vf0 [16];
  undefined1 auVar12 [16];
  undefined1 auVar13 [16];
  
  lVar10 = 0;
  iVar1 = *(int *)(param_4 + 4);
  iVar6 = param_5 * 0x1c + 0x150;
  if ('\0' < *(char *)(iVar1 + iVar6 + 1)) {
    iVar8 = iVar1 + 8;
    piVar9 = (int *)(iVar8 + iVar6);
    auVar13 = _qmtc2(0);
    iVar6 = 0;
    do {
      iVar3 = *(int *)(iVar6 + *(int *)(param_5 * 0x1c + iVar8 + 0x150));
      *(undefined4 *)(iVar3 + 0x28) = 0;
      fVar11 = *(float *)(iVar3 + 0x24) + param_1;
      *(float *)(iVar3 + 0x24) = fVar11;
      while (fGpffff8620 < fVar11) {
        iVar3 = *(int *)(iVar6 + *(int *)(param_5 * 0x1c + iVar8 + 0x150));
        fVar11 = *(float *)(iVar3 + 0x24) - fGpffff8628;
        *(float *)(iVar3 + 0x24) = fVar11;
      }
      fVar11 = *(float *)(*(int *)(iVar6 + *piVar9) + 0x24);
      while (fVar11 < fGpffff8624) {
        iVar3 = *(int *)(iVar6 + *(int *)(param_5 * 0x1c + iVar8 + 0x150));
        fVar11 = *(float *)(iVar3 + 0x24) + fGpffff862c;
        *(float *)(iVar3 + 0x24) = fVar11;
      }
      iVar5 = param_5 * 0x1c + 0x160;
      iVar3 = *(int *)(iVar6 + *piVar9);
      piVar7 = (int *)(iVar6 + *(int *)(iVar1 + iVar5));
      iVar2 = *piVar7;
      _lqc2(*(undefined1 (*) [16])(iVar3 + 0x10));
      auVar12 = _vaddbc(in_vf0,auVar13);
      auVar12 = _sqc2(auVar12);
      *(undefined1 (*) [16])(iVar3 + 0x10) = auVar12;
      *(undefined4 *)(iVar3 + 0x2c) = param_3;
      if (iVar2 != 0) {
        *(ulong *)(iVar2 + 8) = *(ulong *)(iVar2 + 8) & 0xfffffffffffffffe | ~param_6 & 1;
      }
      piVar4 = (int *)(iVar6 + *(int *)(iVar1 + 4 + iVar5));
      iVar3 = *piVar4;
      if (iVar3 != 0) {
        *(ulong *)(iVar3 + 8) = *(ulong *)(iVar3 + 8) & 0xfffffffffffffffe | param_6 & 1;
      }
      if (iGpffffa1e8 != 0) {
        iVar3 = *piVar7;
        if (iVar3 == 0) {
          iVar3 = *piVar4;
        }
        else {
          *(ulong *)(iVar3 + 8) = *(ulong *)(iVar3 + 8) & 0xfffffffffffffffe;
          iVar3 = *piVar4;
        }
        if (iVar3 != 0) {
          *(ulong *)(iVar3 + 8) = *(ulong *)(iVar3 + 8) | 1;
        }
      }
      lVar10 = (long)((int)lVar10 + 1);
      iVar6 = iVar6 + 4;
    } while (lVar10 < *(char *)(param_5 * 0x1c + iVar1 + 0x151));
  }
  return;
}


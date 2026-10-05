
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_002296c8(long param_1,undefined4 *param_2,undefined1 (*param_3) [16])

{
  bool bVar1;
  undefined1 in_zero_qw [16];
  char cVar2;
  undefined1 (*pauVar3) [16];
  long lVar4;
  long lVar5;
  undefined1 auVar6 [16];
  undefined1 auVar7 [16];
  undefined1 auVar8 [16];
  undefined1 auVar9 [16];
  undefined1 auVar10 [16];
  undefined1 auVar11 [16];
  uint uVar12;
  int iVar13;
  int iVar14;
  int iVar15;
  float fVar16;
  float fVar17;
  float fVar18;
  float fVar19;
  float fVar20;
  float fVar21;
  undefined1 in_vf0 [16];
  undefined1 auVar22 [16];
  undefined1 auVar23 [16];
  undefined1 auVar24 [16];
  undefined1 auStack_70 [16];
  undefined1 auStack_60 [16];
  undefined1 auStack_50 [16];
  undefined1 auStack_40 [16];
  
  lVar4 = FUN_0021b710(*param_2);
  iVar15 = (int)param_1;
  if ((param_1 == 0) || (uVar12 = param_2[1], (uVar12 & 0x10000) == 0)) {
    uVar12 = param_2[1];
    auVar7 = _pextlw((long)(int)param_2[4],(long)(int)param_2[3]);
    auVar6 = _pextlw(0x3f800000,(long)(int)param_2[5]);
    auVar6 = _pcpyld(auVar6,auVar7);
    fGpffff9408 = DAT_70003560;
    _DAT_700034a0 = auVar6;
    if ((uVar12 & 0x20000) == 0) {
      auVar6 = _vmove(in_vf0);
      _DAT_70003050 = _sqc2(auVar6);
      auVar6 = _pextlw((long)(int)-(float)param_2[7],(long)(int)param_2[6]);
      auVar6 = _pexcw(auVar6);
      auVar6 = _qmtc2(auVar6._0_4_);
      _vcallms(0x268);
      auVar7 = _qmfc2(auVar6._0_4_);
      auVar22 = _qmfc2(auVar6._0_4_);
      auVar11 = _qmtc2(-(float)param_2[8]);
      _vcallms(0x268);
      auVar6 = _pextuw(in_zero_qw,auVar7);
      auVar8 = _pextuw(in_zero_qw,auVar7);
      auVar24 = _prot3w(auVar7);
      auVar9 = _pextuw(in_zero_qw,auVar6);
      auVar10 = _qmfc2(auVar11._0_4_);
      auVar6 = _qmfc2(auVar11._0_4_);
      auVar11 = _prot3w(auVar6);
      fVar20 = auVar22._0_4_;
      auVar7._8_8_ = 0;
      auVar7._0_8_ = auVar6._8_8_;
      auVar7 = auVar7 << 0x40;
      fVar21 = auVar24._0_4_;
      fVar18 = auVar10._0_4_;
      fVar19 = auVar11._0_4_;
      fVar16 = auVar8._0_4_;
      fVar17 = auVar9._0_4_;
      auVar11 = _pextlw((long)(int)(-fVar18 * fVar17),
                        (long)(int)(fVar19 * fVar21 + fVar18 * fVar20 * fVar16));
      auVar10 = _pextlw((long)(int)(fVar19 * fVar17),
                        (long)(int)(fVar18 * fVar21 - fVar19 * fVar20 * fVar16));
      auVar8 = _pextlw(auVar8._0_8_,(long)(int)(fVar17 * fVar20));
      auVar9 = _pextlw(0,(long)(int)(fVar18 * fVar21 * fVar16 - fVar19 * fVar20));
      auVar6 = _pextlw(0,(long)(int)(fVar17 * fVar21));
      auVar9 = _pcpyld(auVar9,auVar11);
      auVar8 = _pcpyld(auVar6,auVar8);
      auVar6 = _pextlw(0,(long)(int)(-(fVar18 * fVar20) - fVar19 * fVar21 * fVar16));
      auVar6 = _pcpyld(auVar6,auVar10);
      DAT_70003020 = auVar9._0_4_;
      DAT_70003024 = auVar9._4_4_;
      DAT_70003028 = auVar9._8_4_;
      DAT_7000302c = auVar9._12_4_;
      DAT_70003030 = auVar6._0_4_;
      DAT_70003034 = auVar6._4_4_;
      DAT_70003038 = auVar6._8_4_;
      DAT_7000303c = auVar6._12_4_;
      DAT_70003040 = auVar8._0_4_;
      DAT_70003044 = auVar8._4_4_;
      DAT_70003048 = auVar8._8_4_;
      DAT_7000304c = auVar8._12_4_;
      goto LAB_002299e4;
    }
    FUN_00114098(auStack_70);
    uVar12 = param_2[1];
  }
  else {
    auVar22 = _vmove(in_vf0);
    auVar6 = _pextlw((long)(int)-*(float *)(iVar15 + 0x24),(long)*(int *)(iVar15 + 0x20));
    auVar6 = _pexcw(auVar6);
    auVar6 = _qmtc2(auVar6._0_4_);
    _vcallms(0x268);
    auVar7 = _qmfc2(auVar6._0_4_);
    auVar8 = _qmfc2(auVar6._0_4_);
    auVar24 = _qmtc2(-*(float *)(iVar15 + 0x28));
    _vcallms(0x268);
    auVar6 = _pextuw(in_zero_qw,auVar7);
    auVar9 = _pextuw(in_zero_qw,auVar7);
    auVar7 = _prot3w(auVar7);
    auVar10 = _pextuw(in_zero_qw,auVar6);
    auVar11 = _qmfc2(auVar24._0_4_);
    auVar6 = _qmfc2(auVar24._0_4_);
    auVar6 = _prot3w(auVar6);
    fVar17 = auVar8._0_4_;
    fVar18 = auVar7._0_4_;
    fVar21 = auVar11._0_4_;
    fVar16 = auVar6._0_4_;
    auVar6 = _lqc2(*(undefined1 (*) [16])(iVar15 + 0x10));
    _DAT_70003050 = _sqc2(auVar22);
    _sqc2(auVar6);
    fVar19 = auVar9._0_4_;
    auVar6 = _vmove(in_vf0);
    _DAT_700034a0 = _sqc2(auVar6);
    fVar20 = auVar10._0_4_;
    fGpffff9408 = *(float *)(iVar15 + 0x2c) * DAT_70003560;
    auVar10 = _pextlw((long)(int)(-fVar21 * fVar20),
                      (long)(int)(fVar16 * fVar18 + fVar21 * fVar17 * fVar19));
    auVar8 = _pextlw((long)(int)(fVar16 * fVar20),
                     (long)(int)(fVar21 * fVar18 - fVar16 * fVar17 * fVar19));
    auVar7 = _pextlw(auVar9._0_8_,(long)(int)(fVar20 * fVar17));
    auVar11 = _pextlw(0,(long)(int)(fVar21 * fVar18 * fVar19 - fVar16 * fVar17));
    auVar6 = _pextlw(0,(long)(int)(fVar20 * fVar18));
    auVar9 = _pcpyld(auVar6,auVar7);
    auVar7 = _pextlw(0,(long)(int)(-(fVar21 * fVar17) - fVar16 * fVar18 * fVar19));
    auVar10 = _pcpyld(auVar11,auVar10);
    auVar6 = _pcpyld(auVar7,auVar8);
    DAT_70003030 = auVar6._0_4_;
    DAT_70003034 = auVar6._4_4_;
    DAT_70003038 = auVar6._8_4_;
    DAT_7000303c = auVar6._12_4_;
    DAT_70003020 = auVar10._0_4_;
    DAT_70003024 = auVar10._4_4_;
    DAT_70003028 = auVar10._8_4_;
    DAT_7000302c = auVar10._12_4_;
    DAT_70003040 = auVar9._0_4_;
    DAT_70003044 = auVar9._4_4_;
    DAT_70003048 = auVar9._8_4_;
    DAT_7000304c = auVar9._12_4_;
LAB_002299e4:
    auVar6 = _lqc2(*param_3);
    auVar11 = _lqc2(param_3[1]);
    auVar22 = _lqc2(param_3[2]);
    auVar24 = _lqc2(param_3[3]);
    auVar8._4_4_ = DAT_70003024;
    auVar8._0_4_ = DAT_70003020;
    auVar8._8_4_ = DAT_70003028;
    auVar8._12_4_ = DAT_7000302c;
    auVar8 = _lqc2(auVar8);
    auVar9._4_4_ = DAT_70003034;
    auVar9._0_4_ = DAT_70003030;
    auVar9._8_4_ = DAT_70003038;
    auVar9._12_4_ = DAT_7000303c;
    auVar9 = _lqc2(auVar9);
    auVar10._4_4_ = DAT_70003044;
    auVar10._0_4_ = DAT_70003040;
    auVar10._8_4_ = DAT_70003048;
    auVar10._12_4_ = DAT_7000304c;
    auVar10 = _lqc2(auVar10);
    auVar23 = _lqc2(_DAT_70003050);
    _vmulabc(auVar6,auVar8);
    _vmaddabc(auVar11,auVar8);
    _vmaddabc(auVar22,auVar8);
    auVar8 = _vmaddbc(auVar24,auVar8);
    _vmulabc(auVar6,auVar9);
    _vmaddabc(auVar11,auVar9);
    _vmaddabc(auVar22,auVar9);
    auVar9 = _vmaddbc(auVar24,auVar9);
    _vmulabc(auVar6,auVar10);
    _vmaddabc(auVar11,auVar10);
    _vmaddabc(auVar22,auVar10);
    auVar10 = _vmaddbc(auVar24,auVar10);
    _vmulabc(auVar6,auVar23);
    _vmaddabc(auVar11,auVar23);
    _vmaddabc(auVar22,auVar23);
    auVar6 = _vmaddbc(auVar24,auVar23);
    auStack_70 = _sqc2(auVar8);
    auStack_60 = _sqc2(auVar9);
    auStack_50 = _sqc2(auVar10);
    auStack_40 = _sqc2(auVar6);
    auVar6 = auVar7;
  }
  if ((uVar12 & 0x1000000) == 0) {
    if ((uVar12 & 0x10000) == 0) goto LAB_00229ab8;
    auVar6._0_8_ = 0x70000000;
    if (param_1 != 0) {
      if (((*(long *)(iVar15 + 8) << 0x1c) >> 0x20 & 1U) != 0) goto LAB_00229a98;
      goto LAB_00229ab8;
    }
  }
  else {
LAB_00229a98:
    auStack_70 = _DAT_00234280;
    auStack_60 = _DAT_00234290;
    auStack_50 = _DAT_002342a0;
    auVar6 = _DAT_00234280;
LAB_00229ab8:
    auVar6._0_8_ = 0x70000000;
  }
  iVar14 = auVar6._0_4_;
  pauGpffff93f8 = (undefined1 (*) [16])(iVar14 + 0x34a0);
  uGpffff9430 = *param_2;
  pauVar3 = (undefined1 (*) [16])(iGpffff946c * 0x40 + iVar14 + 0x32a0);
  auVar10 = _lqc2(*pauGpffff93f8);
  auVar9 = _lqc2(pauVar3[3]);
  auVar8 = _lqc2(*pauVar3);
  auVar7 = _lqc2(pauVar3[1]);
  auVar6 = _lqc2(pauVar3[2]);
  _vmulabc(auVar8,auVar10);
  _vmaddabc(auVar7,auVar10);
  _vmaddabc(auVar6,auVar10);
  auVar7 = _vmaddbc(auVar9,auVar10);
  auVar6 = _sqc2(auVar7);
  *pauGpffff93f8 = auVar6;
  puGpffff9434 = auStack_70;
  if (lVar4 == 0) {
LAB_00229c58:
    cVar2 = *(char *)(param_2 + 1);
  }
  else {
    iVar13 = (int)lVar4;
    bVar1 = true;
    fVar20 = ABS(*(float *)(iVar13 + 4));
    fVar16 = ABS(*(float *)(iVar13 + 8));
    fVar18 = ABS(*(float *)(iVar13 + 0xc));
    fVar17 = ABS(*(float *)(iVar13 + 0x10));
    fVar21 = ABS(*(float *)(iVar13 + 0x14));
    fVar19 = ABS(*(float *)(iVar13 + 0x18));
    *(undefined4 *)(iVar14 + 0x3060) = auStack_70._0_4_;
    *(undefined4 *)(iVar14 + 0x3064) = auStack_70._4_4_;
    *(undefined4 *)(iVar14 + 0x3068) = auStack_70._8_4_;
    *(undefined4 *)(iVar14 + 0x306c) = auStack_70._12_4_;
    *(int *)(iVar14 + 0x3070) = auStack_60._0_4_;
    *(int *)(iVar14 + 0x3074) = auStack_60._4_4_;
    *(int *)(iVar14 + 0x3078) = auStack_60._8_4_;
    *(int *)(iVar14 + 0x307c) = auStack_60._12_4_;
    *(int *)(iVar14 + 0x3080) = auStack_50._0_4_;
    *(int *)(iVar14 + 0x3084) = auStack_50._4_4_;
    *(int *)(iVar14 + 0x3088) = auStack_50._8_4_;
    *(int *)(iVar14 + 0x308c) = auStack_50._12_4_;
    auVar8 = _pextlw((long)(int)((int)fVar17 * (uint)(fVar18 < fVar17) |
                                (int)fVar18 * (uint)(fVar18 >= fVar17)),
                     (long)(int)((int)fVar16 * (uint)(fVar20 < fVar16) |
                                (int)fVar20 * (uint)(fVar20 >= fVar16)));
    auVar11 = _lqc2(pauGpffff9380[3]);
    auVar6 = _lqc2(*pauGpffff9380);
    auVar10 = _lqc2(pauGpffff9380[1]);
    auVar9 = _lqc2(pauGpffff9380[2]);
    _vmulabc(auVar6,auVar7);
    _vmaddabc(auVar10,auVar7);
    _vmaddabc(auVar9,auVar7);
    auVar6 = _vmaddbc(auVar11,auVar7);
    auVar6 = _sqc2(auVar6);
    *(undefined1 (*) [16])(iVar14 + 0x3090) = auVar6;
    auVar9 = _vmove(in_vf0);
    auVar6 = _pextlw(0x3f800000,
                     (long)(int)((int)fVar19 * (uint)(fVar21 < fVar19) |
                                (int)fVar21 * (uint)(fVar21 >= fVar19)));
    auVar7 = _pcpyld(auVar6,auVar8);
    auVar6 = _sqc2(auVar9);
    *(undefined1 (*) [16])(iVar14 + 0x3090) = auVar6;
    *(int *)(iVar14 + 0x34e0) = auVar7._0_4_;
    *(int *)(iVar14 + 0x34e4) = auVar7._4_4_;
    *(int *)(iVar14 + 0x34e8) = auVar7._8_4_;
    *(int *)(iVar14 + 0x34ec) = auVar7._12_4_;
    puGpffff9434 = auStack_70;
    if ((iGpffff93e0 == 0) &&
       (puGpffff9434 = auStack_70, lVar5 = FUN_0022a110(lVar4,pauGpffff93f8), lVar5 != 0)) {
      lVar5 = FUN_00229d50(iVar13 + 4,auStack_70);
      bVar1 = lVar5 == 0;
    }
    else {
      DAT_700035a0 = 0;
    }
    if (bVar1) {
      if (*(short *)(iVar13 + 0x1c) != 0) {
        FUN_00229fa8(*param_2,lVar4,DAT_700035a0,0);
      }
      if (*(short *)(iVar13 + 0x28) != 0) {
        if ((DAT_700035a0 & 0xa2a) != 0) {
          FUN_0022a048(*param_2,1);
          cVar2 = *(char *)(param_2 + 1);
          goto LAB_00229c5c;
        }
        FUN_0022a048(*param_2,0);
      }
      goto LAB_00229c58;
    }
    cVar2 = *(char *)(param_2 + 1);
  }
LAB_00229c5c:
  if (cVar2 == '\0') {
    return;
  }
  iGpffff946c = iGpffff946c + 1;
  FUN_0021b7a8(auStack_70,pauGpffff9380,pauGpffff93f8);
  iVar14 = param_2[10];
  if (param_1 == 0) {
    uVar12 = (uint)*(byte *)(param_2 + 1);
  }
  else {
    iVar15 = *(int *)(iVar15 + 4);
    uVar12 = (uint)*(byte *)(param_2 + 1);
    if (iVar15 != 0) {
      if (uVar12 != 0) {
        do {
          if ((*(uint *)(iVar14 + 4) & 0x10000) == 0) {
            iVar13 = iVar15 + 0x10;
            FUN_002296c8(iVar15,iVar14,auStack_70);
          }
          else {
            if ((*(uint *)(iVar15 + 8) & 1) != 0) {
              FUN_002296c8(iVar15,iVar14,auStack_70);
            }
            iVar13 = iVar15 + 0x40;
          }
          uVar12 = uVar12 - 1;
          iVar14 = iVar14 + 0x2c;
          iVar15 = iVar13;
        } while (0 < (int)uVar12);
      }
      goto LAB_00229d28;
    }
  }
  if (uVar12 != 0) {
    do {
      uVar12 = uVar12 - 1;
      FUN_002296c8(0,iVar14,auStack_70);
      iVar14 = iVar14 + 0x2c;
    } while (0 < (int)uVar12);
  }
LAB_00229d28:
  iGpffff946c = iGpffff946c + -1;
  return;
}


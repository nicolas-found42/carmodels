
void FUN_001be798(undefined8 param_1,int param_2)

{
  int iVar1;
  int iVar2;
  undefined1 auVar3 [12];
  undefined1 in_zero_qw [16];
  undefined8 uVar4;
  undefined8 extraout_v0_udw;
  float fVar5;
  undefined1 auVar6 [16];
  int iVar7;
  undefined1 auVar8 [16];
  char *pcVar9;
  float fVar10;
  float fVar11;
  uint uVar12;
  float fVar13;
  float fVar14;
  float fVar15;
  float fVar16;
  float fVar17;
  float fVar18;
  float fVar19;
  float fVar20;
  float fVar21;
  float fVar22;
  float fVar23;
  float fVar24;
  undefined1 in_vf0 [16];
  undefined1 auVar25 [16];
  undefined1 auVar26 [16];
  undefined1 auVar27 [16];
  undefined1 auVar28 [16];
  undefined1 auVar29 [16];
  float fStack_110;
  float fStack_10c;
  float fStack_108;
  undefined8 uStack_100;
  undefined4 uStack_f0;
  undefined4 uStack_ec;
  undefined4 uStack_e8;
  undefined4 uStack_e4;
  
  auVar27 = ZEXT816(0);
  pcVar9 = (char *)param_1;
  fStack_10c = 0.0;
  fVar24 = 0.0;
  auVar8 = _pextlw(0,0);
  iVar1 = *(int *)(&DAT_00241bf4 + *pcVar9 * 0x150);
  auVar8 = _pcpyld(auVar8,auVar8);
  iVar2 = *(int *)(&DAT_00241c0c + (*pcVar9 * 0x54 + (int)*(char *)(param_2 + 4)) * 4);
  fStack_108 = 0.0;
  if (*(char *)(param_2 + 4) < '\x02') {
    FUN_001147b8(*(float *)(*(int *)(param_2 + 0x120) + 0xf8) + *(float *)(pcVar9 + 0x14),
                 *(int *)(param_2 + 0x120) + 0x10,param_2 + 0x90);
    iVar7 = *(int *)(param_2 + 0x120);
  }
  else {
    auVar28 = _lqc2(*(undefined1 (*) [16])(param_2 + 0x90));
    iVar7 = *(int *)(param_2 + 0x120);
    auVar25 = _sqc2(auVar28);
    *(undefined1 (*) [16])(iVar7 + 0x20) = auVar25;
    auVar25 = _lqc2(*(undefined1 (*) [16])(pcVar9 + 0x50));
    _vopmula(auVar28,auVar25);
    auVar25 = _vopmsub(auVar25,auVar28);
    auVar29 = _vsub(auVar25,auVar25);
    _vopmula(auVar29,auVar28);
    auVar25 = _vopmsub(auVar28,auVar29);
    auVar28 = _vsub(auVar25,auVar25);
    auVar25 = _sqc2(auVar29);
    *(undefined1 (*) [16])(iVar7 + 0x10) = auVar25;
    auVar25 = _sqc2(auVar28);
    *(undefined1 (*) [16])(iVar7 + 0x30) = auVar25;
  }
  _lqc2(*(undefined1 (*) [16])(iVar7 + 0x40));
  auVar25 = _qmtc2(0);
  fVar23 = *(float *)(iVar7 + 0x11c) * FLOAT_002901c0 + *(float *)(iVar2 + 0x34);
  auVar25 = _vmulbc(in_vf0,auVar25);
  auVar25 = _sqc2(auVar25);
  *(undefined1 (*) [16])(iVar7 + 0x40) = auVar25;
  if (fVar23 <= 0.0) {
    *(undefined4 *)(iVar7 + 0x90) = 0;
    *(undefined4 *)(iVar7 + 0x94) = 0;
    *(undefined4 *)(iVar7 + 0x98) = 0;
    *(undefined4 *)(iVar7 + 0x9c) = 0;
    *(undefined4 *)(iVar7 + 0x100) = 0;
    *(undefined4 *)(iVar7 + 0xa0) = 0;
    *(undefined4 *)(iVar7 + 0xa4) = 0;
    *(undefined4 *)(iVar7 + 0xa8) = 0;
    *(undefined4 *)(iVar7 + 0xac) = 0;
    *(undefined4 *)(iVar7 + 0x110) = 0x3f800000;
    *(undefined4 *)(iVar7 + 0xd8) = 0;
    *(undefined4 *)(iVar7 + 0xfc) = 0x3f800000;
    *(undefined4 *)(iVar7 + 0x104) = 0x3f800000;
    *(undefined4 *)(iVar7 + 0x10c) = 0x3f800000;
    return;
  }
  auVar28 = _lqc2(*(undefined1 (*) [16])(pcVar9 + 0x5f0));
  auVar25 = _lqc2(*(undefined1 (*) [16])(param_2 + 0x60));
  _vopmula(auVar25,auVar28);
  auVar25 = _vopmsub(auVar28,auVar25);
  auVar28 = _lqc2(*(undefined1 (*) [16])(pcVar9 + 0x650));
  auVar25 = _vsub(auVar25,auVar25);
  auVar25 = _vadd(auVar28,auVar25);
  auVar25 = _sqc2(auVar25);
  uStack_100._0_4_ = auVar25._0_4_;
  uStack_100._4_4_ = auVar25._4_4_;
  uStack_f0 = (undefined4)uStack_100;
  uStack_ec = uStack_100._4_4_;
  uStack_e8 = auVar25._8_4_;
  uStack_e4 = auVar25._12_4_;
  fVar11 = (float)FUN_001151d8();
  if (0.0 < fVar11) {
    uStack_100 = auVar25._0_8_;
    uVar4 = FUN_001150f0(fVar11,uStack_100);
    uStack_f0 = (undefined4)uVar4;
    uStack_ec = (undefined4)((ulong)uVar4 >> 0x20);
    uStack_e8 = (undefined4)extraout_v0_udw;
    uStack_e4 = (undefined4)((ulong)extraout_v0_udw >> 0x20);
    iVar7 = *(int *)(param_2 + 0x120);
  }
  else {
    iVar7 = *(int *)(param_2 + 0x120);
  }
  auVar29 = _lqc2(auVar25);
  auVar28 = _lqc2(*(undefined1 (*) [16])(iVar7 + 0x30));
  auVar28 = _vmul(auVar29,auVar28);
  auVar28 = _vaddbc(auVar28,auVar28);
  auVar28 = _vaddbc(auVar28,auVar28);
  auVar28 = _qmfc2(auVar28._0_4_);
  fVar17 = auVar28._0_4_;
  fVar22 = *(float *)(iVar2 + 0x28) * 6.283185 * *(float *)(iVar7 + 0xec) * 0.016666666;
  if (fVar17 == 0.0) {
    *(undefined4 *)(iVar7 + 0x100) = 0x41a00000;
  }
  else {
    *(float *)(iVar7 + 0x100) = (1.0 - ABS(fVar22 / fVar17)) * 100.0;
  }
  fStack_110 = 1.0;
  if (fVar17 < fVar22) {
    fStack_110 = -1.0;
  }
  fVar10 = ABS(*(float *)(iVar7 + 0x100));
  *(float *)(iVar7 + 0x100) = fVar10;
  if (0.0 <= fVar10) {
    uVar12 = (int)fVar10 * (uint)(fVar10 < 100.0) | (uint)(fVar10 >= 100.0) * 0x42c80000;
  }
  else {
    uVar12 = 0;
  }
  *(uint *)(iVar7 + 0x100) = uVar12;
  fVar10 = (float)FUN_001bf648(fVar23,param_1);
  iVar7 = *(int *)(param_2 + 0x120);
  auVar28 = _pextlw(0,0);
  auVar28 = _pcpyld(auVar28,auVar28);
  fVar11 = fVar11 * 0.39999998 * fVar11 * 0.39999998;
  fVar11 = fVar11 * fVar11;
  *(float *)(iVar7 + 0xd8) = fVar10;
  if (0.0 <= fVar11) {
    fVar11 = (float)((int)fVar11 * (uint)(fVar11 < 1.0) | (uint)(fVar11 >= 1.0) * 0x3f800000);
  }
  else {
    fVar11 = 0.0;
  }
  auVar26 = _lqc2(*(undefined1 (*) [16])(iVar7 + 0x10));
  auVar29._4_4_ = uStack_ec;
  auVar29._0_4_ = uStack_f0;
  auVar29._8_4_ = uStack_e8;
  auVar29._12_4_ = uStack_e4;
  auVar29 = _lqc2(auVar29);
  auVar29 = _vmul(auVar26,auVar29);
  auVar29 = _vaddbc(auVar29,auVar29);
  auVar29 = _vaddbc(auVar29,auVar29);
  auVar6 = _qmfc2(auVar29._0_4_);
  auVar26._4_4_ = uStack_ec;
  auVar26._0_4_ = uStack_f0;
  auVar26._8_4_ = uStack_e8;
  auVar26._12_4_ = uStack_e4;
  auVar29 = _lqc2(auVar26);
  auVar26 = _lqc2(*(undefined1 (*) [16])(iVar7 + 0x30));
  auVar29 = _vmul(auVar26,auVar29);
  auVar29 = _vaddbc(auVar29,auVar29);
  auVar29 = _vaddbc(auVar29,auVar29);
  auVar29 = _qmfc2(auVar29._0_4_);
  fVar19 = 1.0;
  fVar20 = ABS(auVar29._0_4_);
  if (auVar6._0_4_ < 0.0) {
    fVar19 = -1.0;
  }
  if (0.0 <= fVar20) {
    fVar20 = (float)((int)fVar20 * (uint)(fVar20 < 1.0) | (uint)(fVar20 >= 1.0) * 0x3f800000);
  }
  else {
    fVar20 = 0.0;
  }
  fVar13 = (float)FUN_00204ea0();
  fVar21 = *(float *)(*(int *)(param_2 + 0x120) + 0x100);
  fVar14 = fStack_110 * fVar21;
  fVar20 = fVar20 * fVar19;
  fVar15 = (float)FUN_001bf7f8(fVar21,fVar13,
                               *(undefined4 *)
                                (&DAT_00241c0c + (*pcVar9 * 0x54 + (int)*(char *)(param_2 + 4)) * 4)
                              );
  fVar16 = (float)FUN_001bf988(fVar21,fVar13,
                               *(undefined4 *)
                                (&DAT_00241c0c + (*pcVar9 * 0x54 + (int)*(char *)(param_2 + 4)) * 4)
                              );
  iVar7 = *(int *)(param_2 + 0x120);
  auVar26 = _pextlw(0,(long)(int)(fVar16 * fVar19 * fVar10));
  auVar29 = _pextlw(0,(long)(int)(fVar15 * fStack_110 * fVar10));
  auVar29 = _pcpyld(auVar29,auVar26);
  if (60.0 < ABS(*(float *)(iVar7 + 0xec))) {
    if (*(float *)(iVar1 + 0x18) != 0.0) {
      auVar8 = _lqc2(*(undefined1 (*) [16])(iVar7 + 0x90));
      fVar19 = auVar29._0_4_;
      auVar8 = _qmfc2(auVar8._0_4_);
      fVar5 = auVar8._0_4_;
      fVar18 = ABS(*(float *)(iVar1 + 0x18) * *(float *)(iVar7 + 0xf0) * 0.15915494);
      if (ABS(fVar19) < ABS(fVar5)) {
        fVar18 = fVar18 * 5.0;
      }
      _qmtc2(fVar19);
      auVar8 = _qmtc2(fVar5 + (fVar19 - fVar5) *
                              (float)((int)fVar18 * (uint)(fVar18 < 1.0) |
                                     (uint)(fVar18 >= 1.0) * 0x3f800000));
      auVar29 = _vaddbc(in_vf0,auVar8);
      auVar8 = _vaddbc(in_vf0,auVar8);
      auVar29 = _qmfc2(auVar29._0_4_);
      auVar8 = _sqc2(auVar8);
      *(undefined1 (*) [16])(iVar7 + 0x90) = auVar8;
      goto LAB_001becbc;
    }
    _lqc2(*(undefined1 (*) [16])(iVar7 + 0x90));
  }
  else {
    _lqc2(*(undefined1 (*) [16])(iVar7 + 0x90));
  }
  auVar8 = _qmtc2(auVar8._0_4_);
  auVar8 = _vmove(auVar8);
  auVar8 = _sqc2(auVar8);
  *(undefined1 (*) [16])(iVar7 + 0x90) = auVar8;
LAB_001becbc:
  fVar22 = fVar22 - fVar17;
  if (fVar11 < 1.0) {
    fStack_10c = *(float *)(iVar7 + 0x100);
    fVar17 = *(float *)(pcVar9 + 0xc);
    fVar19 = ABS(fVar22) * FLOAT_002901cc;
    fVar24 = fStack_110 * fStack_10c;
    fStack_108 = (float)FUN_001bf7f8(fStack_10c,0,
                                     *(undefined4 *)
                                      (&DAT_00241c0c +
                                      (*pcVar9 * 0x54 + (int)*(char *)(param_2 + 4)) * 4));
    iVar7 = *(int *)(param_2 + 0x120);
    auVar27 = _lqc2(auVar25);
    auVar8 = _lqc2(*(undefined1 (*) [16])(iVar7 + 0x10));
    auVar8 = _vmul(auVar27,auVar8);
    auVar8 = _vaddbc(auVar8,auVar8);
    auVar8 = _vaddbc(auVar8,auVar8);
    auVar8 = _qmfc2(auVar8._0_4_);
    _qmtc2(auVar28._0_4_);
    auVar27 = _pextlw(0,(long)(int)(fStack_108 * fStack_110 * fVar19 * fVar17));
    auVar8 = _pextlw(0,(long)(int)(auVar8._0_4_ * FLOAT_002901cc * *(float *)(pcVar9 + 0xc) * 0.25))
    ;
    auVar27 = _pcpyld(auVar27,auVar8);
    auVar8 = _qmtc2(auVar27._0_4_);
    auVar8 = _vmove(auVar8);
    auVar28 = _qmfc2(auVar8._0_4_);
  }
  fVar17 = (float)FUN_001bf988(*(undefined4 *)(iVar7 + 0x100),0.24434607,
                               *(undefined4 *)
                                (&DAT_00241c0c + (*pcVar9 * 0x54 + (int)*(char *)(param_2 + 4)) * 4)
                              );
  *(float *)(*(int *)(param_2 + 0x120) + 0xd0) = fVar10 * fVar17;
  fVar17 = (float)FUN_001bf7f8(0x41600000,fVar13,
                               *(undefined4 *)
                                (&DAT_00241c0c + (*pcVar9 * 0x54 + (int)*(char *)(param_2 + 4)) * 4)
                              );
  iVar1 = *(int *)(param_2 + 0x120);
  *(float *)(iVar1 + 0xd4) = fVar10 * fVar17;
  if (1.0 <= fVar11) {
    auVar3 = *(undefined1 (*) [12])(iVar1 + 0x90);
    auVar8 = _por(in_zero_qw,auVar29);
    *(float *)(iVar1 + 0x10c) = fVar16;
    *(int *)(iVar1 + 0xa0) = auVar3._0_4_;
    *(int *)(iVar1 + 0xa4) = auVar3._4_4_;
    *(int *)(iVar1 + 0xa8) = auVar3._8_4_;
    *(undefined4 *)(iVar1 + 0xac) = *(undefined4 *)(iVar1 + 0x9c);
    *(float *)(iVar1 + 0x110) = fVar15;
    *(float *)(iVar1 + 0x104) = fVar20;
    *(float *)(iVar1 + 0xfc) = fVar13;
    *(float *)(iVar1 + 0x100) = fVar21;
    *(float *)(iVar1 + 0x108) = fVar14;
  }
  else {
    auVar26 = _qmtc2(auVar28._0_4_);
    auVar6 = _qmtc2(auVar29._0_4_);
    auVar8 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x90));
    auVar8 = _vsub(auVar8,auVar26);
    auVar29 = _qmtc2(fVar11);
    auVar8 = _vmulbc(auVar8,auVar29);
    auVar26 = _qmtc2(auVar27._0_4_);
    auVar26 = _vsub(auVar6,auVar26);
    auVar28 = _qmtc2(auVar28._0_4_);
    auVar8 = _vadd(auVar8,auVar28);
    auVar8 = _sqc2(auVar8);
    *(undefined1 (*) [16])(iVar1 + 0xa0) = auVar8;
    auVar28 = _vmulbc(auVar26,auVar29);
    auVar8 = _qmtc2(auVar27._0_4_);
    auVar8 = _vadd(auVar28,auVar8);
    auVar8 = _qmfc2(auVar8._0_4_);
    *(float *)(iVar1 + 0x10c) = fVar11 * (fVar16 - 0.0) + 0.0;
    *(float *)(iVar1 + 0x110) = fStack_108 + fVar11 * (fVar15 - fStack_108);
    *(float *)(iVar1 + 0x104) = fVar11 * (fVar20 - 0.0) + 0.0;
    *(float *)(iVar1 + 0xfc) = fVar11 * (fVar13 - 0.0) + 0.0;
    *(float *)(iVar1 + 0x108) = fVar24 + fVar11 * (fVar14 - fVar24);
    *(float *)(iVar1 + 0x100) = fStack_10c + fVar11 * (fVar21 - fStack_10c);
  }
  fVar24 = auVar8._0_4_;
  auVar27 = _qmtc2(fVar24);
  auVar29 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x30));
  _vmove(auVar27);
  auVar28 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x10));
  auVar27 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x20));
  fVar11 = ABS(*(float *)(iVar1 + 0xec)) * 0.0033333332;
  auVar26 = _qmtc2(fVar24);
  _vmulabc(auVar28,auVar26);
  _vmaddabc(auVar27,auVar26);
  auVar27 = _vmaddbc(auVar29,auVar26);
  auVar27 = _sqc2(auVar27);
  *(undefined1 (*) [16])(iVar1 + 0x80) = auVar27;
  if (0.0 <= fVar11) {
    fVar11 = (float)((int)fVar11 * (uint)(fVar11 < 1.0) | (uint)(fVar11 >= 1.0) * 0x3f800000);
  }
  else {
    fVar11 = 0.0;
  }
  auVar27 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x10));
  auVar25 = _lqc2(auVar25);
  auVar27 = _vmul(auVar27,auVar25);
  auVar27 = _vaddbc(auVar27,auVar27);
  auVar27 = _vaddbc(auVar27,auVar27);
  auVar27 = _qmfc2(auVar27._0_4_);
  fVar17 = ABS(fVar23 * fVar22 * FLOAT_002901cc);
  fVar19 = (float)((int)fVar17 * (uint)(fVar17 < fVar10) | (int)fVar10 * (uint)(fVar17 >= fVar10));
  fVar22 = ABS(*(float *)(iVar2 + 0x34) * fVar22 * FLOAT_002901cc);
  fVar23 = ABS(fVar23 * auVar27._0_4_ * FLOAT_002901cc);
  fVar17 = (float)((int)fVar23 * (uint)(fVar23 < fVar10) | (int)fVar10 * (uint)(fVar23 >= fVar10));
  fVar23 = -fVar17;
  fVar22 = ((fVar11 + fVar11) * fVar22 + fVar22) * *(float *)(iVar2 + 0x28);
  fVar22 = (float)((int)fVar22 * (uint)(fVar22 < fVar19) | (int)fVar19 * (uint)(fVar22 >= fVar19));
  if (fVar23 <= fVar24) {
    fVar23 = (float)((int)fVar24 * (uint)(fVar24 < fVar17) | (int)fVar17 * (uint)(fVar24 >= fVar17))
    ;
  }
  fVar17 = -fVar19;
  auVar8 = _pextuw(in_zero_qw,auVar8);
  fVar24 = auVar8._0_4_;
  if (fVar17 <= fVar24) {
    fVar17 = (float)((int)fVar24 * (uint)(fVar24 < fVar19) | (int)fVar19 * (uint)(fVar24 >= fVar19))
    ;
  }
  fVar10 = -fVar22;
  auVar27 = _pextlw(0,(long)(int)fVar23);
  auVar8 = _pextlw(0,(long)(int)fVar17);
  auVar27 = _pcpyld(auVar8,auVar27);
  auVar8 = _pextuw(in_zero_qw,auVar27);
  fVar24 = auVar8._0_4_;
  if (fVar10 <= fVar24) {
    fVar10 = (float)((int)fVar24 * (uint)(fVar24 < fVar22) | (int)fVar22 * (uint)(fVar24 >= fVar22))
    ;
  }
  _lqc2(*(undefined1 (*) [16])(iVar1 + 0xa0));
  auVar8 = _qmtc2(auVar27._0_4_);
  _vmove(auVar8);
  auVar25 = _qmtc2(auVar27._0_4_);
  auVar26 = _qmtc2(0);
  auVar6 = _qmtc2(0xbf800000);
  auVar8 = _qmtc2(fVar10 + fVar11 * (fVar24 - fVar10));
  auVar8 = _vaddbc(in_vf0,auVar8);
  auVar8 = _sqc2(auVar8);
  *(undefined1 (*) [16])(iVar1 + 0xa0) = auVar8;
  auVar27 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x20));
  auVar29 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x30));
  auVar8 = _lqc2(*(undefined1 (*) [16])(param_2 + 0x60));
  auVar28 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x10));
  _vmulabc(auVar28,auVar25);
  _vmaddabc(auVar27,auVar25);
  _vmaddbc(auVar29,auVar25);
  auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar9 + 0x490));
  _vsub(auVar8,auVar27);
  auVar8 = _vmulbc(in_vf0,auVar26);
  auVar25 = _vmulbc(auVar8,auVar6);
  auVar27 = _vmulbc(in_vf0,auVar26);
  _vopmula(auVar8,auVar27);
  auVar8 = _vopmsub(auVar27,auVar8);
  auVar8 = _vsub(auVar8,auVar8);
  auVar8 = _vmulbc(auVar8,auVar6);
  auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar9 + 0x500));
  auVar25 = _vadd(auVar25,auVar27);
  auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar9 + 0x4b0));
  auVar8 = _vadd(auVar8,auVar27);
  auVar8 = _sqc2(auVar8);
  *(undefined1 (*) [16])(pcVar9 + 0x4b0) = auVar8;
  auVar8 = _sqc2(auVar25);
  *(undefined1 (*) [16])(pcVar9 + 0x500) = auVar8;
  return;
}


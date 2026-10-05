
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/track/trackini.c:618, 657, 1122, 1162, 1177, 1228, 1236, 1242, 1500, 1623 */

void FUN_0012d4b8(int param_1,undefined4 param_2)

{
  undefined1 *puVar1;
  bool bVar2;
  undefined1 auVar3 [8];
  undefined1 in_zero_qw [16];
  undefined4 uVar4;
  int iVar5;
  float *pfVar6;
  int iVar7;
  undefined4 *puVar8;
  undefined8 uVar9;
  long lVar10;
  long lVar11;
  ulong uVar12;
  undefined8 uVar13;
  undefined8 uVar14;
  undefined8 uVar15;
  undefined1 auVar16 [16];
  undefined1 auVar17 [16];
  undefined8 in_a0_udw;
  undefined1 auVar18 [16];
  undefined1 auVar19 [16];
  undefined8 in_t0_udw;
  undefined1 auVar20 [16];
  undefined1 auVar21 [16];
  undefined1 auVar22 [16];
  undefined1 auVar23 [16];
  undefined1 auVar24 [16];
  undefined *puVar25;
  undefined *puVar26;
  int iVar27;
  char *pcVar28;
  long lVar29;
  undefined1 in_s0_qw [16];
  int *piVar30;
  undefined1 (*pauVar31) [16];
  uint uVar32;
  uint uVar33;
  int *piVar34;
  undefined4 *puVar35;
  int iVar36;
  uint uVar37;
  uint uVar38;
  float fVar39;
  float fVar40;
  float fVar41;
  float fVar42;
  float fVar43;
  float fVar44;
  float fVar45;
  float fVar46;
  float fVar47;
  float fVar48;
  float fVar49;
  float fVar50;
  int iVar51;
  undefined1 auVar52 [16];
  undefined1 auStack_2c0 [256];
  undefined1 auStack_1c0 [8];
  undefined1 auStack_1b8 [8];
  undefined1 auStack_1b0 [16];
  undefined1 auStack_1a0 [8];
  undefined1 auStack_198 [8];
  undefined1 auStack_190 [16];
  undefined1 auStack_180 [16];
  undefined1 auStack_170 [16];
  undefined1 auStack_160 [16];
  undefined1 auStack_150 [16];
  undefined1 auStack_140 [16];
  undefined4 uStack_130;
  undefined4 uStack_12c;
  undefined4 uStack_128;
  undefined4 uStack_124;
  undefined4 uStack_120;
  undefined4 uStack_11c;
  undefined4 uStack_118;
  undefined4 uStack_114;
  undefined4 uStack_110;
  undefined4 uStack_10c;
  undefined4 uStack_108;
  undefined4 uStack_104;
  undefined4 uStack_100;
  undefined4 uStack_fc;
  undefined4 uStack_f8;
  undefined4 uStack_f4;
  undefined4 uStack_f0;
  undefined4 uStack_ec;
  undefined4 uStack_e8;
  undefined4 uStack_e4;
  undefined4 uStack_e0;
  undefined4 uStack_dc;
  undefined4 uStack_d8;
  undefined4 uStack_d4;
  undefined4 uStack_d0;
  undefined4 uStack_cc;
  undefined4 uStack_c8;
  undefined4 uStack_c4;
  uint uStack_c0;
  int iStack_bc;
  int iStack_b8;
  int iStack_b4;
  int iStack_b0;
  int iStack_ac;
  int iStack_a8;
  int iStack_a4;
  int iStack_a0;
  undefined1 auStack_90 [16];
  undefined4 uStack_80;
  undefined4 uStack_7c;
  undefined4 uStack_78;
  undefined4 uStack_74;
  
  uStack_80 = in_s0_qw._0_4_;
  uStack_7c = in_s0_qw._4_4_;
  uStack_78 = in_s0_qw._8_4_;
  uStack_74 = in_s0_qw._12_4_;
  iStack_b4 = param_1;
  FUN_00134860();
  FUN_0012f1a0();
  if (iStack_b4 == 0) {
                    /* WARNING: Subroutine does not return */
    FUN_00105888(0x2530d0,0x26a,0x2530f0);
  }
  uVar14 = in_s0_qw._8_8_;
  puVar25 = &DAT_00340320;
  FUN_001017d0(0x340320,0x100,iStack_b4);
  *(undefined4 *)(puVar25 + 0x100) = param_2;
  auVar16._0_8_ = (long)iStack_b4;
  auVar16._8_8_ = in_t0_udw;
  FUN_00101730(auStack_2c0,0x100,0x28f268,0x340ed0,auVar16._0_8_);
  uVar9 = FUN_0011ed90(auStack_2c0);
  *(int *)(puVar25 + 0x188) = (int)uVar9;
  uVar4 = FUN_00124cb8(uVar9,0x28f270);
  *(undefined4 *)(puVar25 + 0x18c) = uVar4;
  uVar4 = FUN_00124cb8(*(undefined4 *)(puVar25 + 0x188),0x253128);
  *(undefined4 *)(puVar25 + 400) = uVar4;
  FUN_00101730(auStack_2c0,0x100,0x253138,iStack_b4);
  lVar10 = FUN_00124cb8(*(undefined4 *)(puVar25 + 0x188),auStack_2c0);
  *(int *)(puVar25 + 0x194) = (int)lVar10;
  if (lVar10 == -1) {
                    /* WARNING: Subroutine does not return */
    FUN_00105888(0x2530d0,0x291,0x253148,iStack_b4);
  }
  lVar10 = FUN_001213d8();
  *(int *)(puVar25 + 0x14c) = (int)lVar10;
  if (lVar10 != 0) {
    iVar36 = 0;
    uVar4 = FUN_001255b0(*(undefined4 *)(puVar25 + 0x194));
    *(undefined4 *)(puVar25 + 0x5a0) = uVar4;
    iVar5 = FUN_001255f8(*(undefined4 *)(puVar25 + 0x194));
    if (0 < *(int *)(puVar25 + 0x5a0)) {
      uVar9 = 0;
      auVar16 = _pextlw(0,0);
      auVar18 = _pextlw(0x3f800000,0);
      auVar16 = _pcpyld(auVar16,auVar18);
      auVar18 = _qmtc2(auVar16._0_4_);
      pauVar31 = (undefined1 (*) [16])(puVar25 + 0x5d0);
      do {
        fVar43 = *(float *)(iVar5 + 0xc);
        iVar36 = iVar36 + 1;
        fVar45 = *(float *)(iVar5 + 0x14);
        fVar40 = *(float *)(iVar5 + 0x10);
        auVar16 = _pextlw(uVar9,(long)(int)fVar43);
        auVar17 = _pextlw(uVar9,(long)(int)fVar40);
        fVar39 = *(float *)(iVar5 + 4);
        fVar42 = *(float *)(iVar5 + 8);
        auVar16 = _pcpyld(auVar17,auVar16);
        auStack_90 = _sqc2(auVar18);
        auVar16 = _qmtc2(auVar16._0_4_);
        _vopmula(auVar16,auVar18);
        auVar16 = _vopmsub(auVar18,auVar16);
        auVar18 = _pextlw(uVar9,(long)(int)fVar39);
        auVar52 = _vsub(auVar16,auVar16);
        auVar16 = _sqc2(auVar52);
        *pauVar31 = auVar16;
        auVar16 = _pextlw(uVar9,(long)(int)fVar42);
        auVar17 = _pcpyld(auVar16,auVar18);
        iVar5 = iVar5 + 0x1c;
        auVar19 = _pextlw(uVar9,(long)(int)(fVar39 + fVar43 * fVar45));
        auVar16 = _pextlw(uVar9,(long)(int)(fVar42 + fVar40 * fVar45));
        auVar18 = _qmfc2(auVar52._0_4_);
        auVar16 = _pcpyld(auVar16,auVar19);
        *(int *)pauVar31[-2] = auVar17._0_4_;
        *(int *)(pauVar31[-2] + 4) = auVar17._4_4_;
        *(int *)(pauVar31[-2] + 8) = auVar17._8_4_;
        *(int *)(pauVar31[-2] + 0xc) = auVar17._12_4_;
        *(int *)pauVar31[-1] = auVar16._0_4_;
        *(int *)(pauVar31[-1] + 4) = auVar16._4_4_;
        *(int *)(pauVar31[-1] + 8) = auVar16._8_4_;
        *(int *)(pauVar31[-1] + 0xc) = auVar16._12_4_;
        uVar4 = FUN_00115070(auVar18._0_8_);
        in_a0_udw = auVar18._8_8_;
        auVar16 = _lqc2(pauVar31[-2]);
        auVar18 = _qmtc2(uVar4);
        iVar7 = *(int *)(puVar25 + 0x5a0);
        auVar16 = _vmul(auVar16,auVar18);
        auVar16 = _vaddbc(auVar16,auVar16);
        auVar16 = _vaddbc(auVar16,auVar16);
        auVar16 = _qmfc2(auVar16._0_4_);
        auVar18 = _sqc2(auVar18);
        *pauVar31 = auVar18;
        *(int *)pauVar31[3] = auVar16._0_4_;
        pauVar31 = pauVar31 + 6;
        auVar18 = _lqc2(auStack_90);
      } while (iVar36 < iVar7);
    }
  }
  puVar25 = &DAT_00340320;
  FUN_00101730(auStack_2c0,0x100,0x253188,iStack_b4);
  *(undefined4 *)(puVar25 + 0x150) = 0;
  lVar10 = FUN_00124cb8(*(undefined4 *)(puVar25 + 0x188),auStack_2c0);
  *(int *)(puVar25 + 0x198) = (int)lVar10;
  if (lVar10 != -1) {
    uVar4 = FUN_001213d8();
    *(undefined4 *)(puVar25 + 0x150) = uVar4;
  }
  *(undefined4 *)(puVar25 + 0x138) = 0;
  lVar10 = 0;
  fVar43 = *(float *)(puVar25 + 0x138);
  fVar39 = fVar43;
  fVar40 = fVar43;
  fVar42 = fVar43;
  if (0 < *(short *)(*(int *)(puVar25 + 0x14c) + 8)) {
    iVar5 = 0;
    do {
      if (lVar10 == 0) {
        fVar40 = *(float *)(*(int *)(*(int *)(puVar25 + 0x14c) + 0x30) + 0x14);
        fVar43 = *(float *)(*(int *)(*(int *)(puVar25 + 0x14c) + 0x30) + 0xc);
        fVar39 = fVar43;
        fVar42 = fVar40;
      }
      puVar26 = &DAT_00340320;
      pfVar6 = (float *)FUN_00126a28(*(undefined4 *)(iVar5 + *(int *)(DAT_0034046c + 0x30)));
      if (pfVar6[1] == -*pfVar6) {
        *(float *)(puVar26 + 0x138) = pfVar6[1] - *pfVar6;
        iVar36 = *(int *)(puVar26 + 0x14c);
      }
      else {
        iVar36 = *(int *)(puVar26 + 0x14c);
      }
      lVar10 = (long)((int)lVar10 + 1);
      iVar7 = iVar5 + *(int *)(iVar36 + 0x30);
      iVar5 = iVar5 + 0x24;
      fVar41 = *(float *)(iVar7 + 0x14);
      fVar45 = *(float *)(iVar7 + 0xc);
      fVar40 = (float)((int)fVar41 * (uint)(fVar40 < fVar41) |
                      (int)fVar40 * (uint)(fVar40 >= fVar41));
      fVar42 = (float)((int)fVar41 * (uint)(fVar41 < fVar42) |
                      (int)fVar42 * (uint)(fVar41 >= fVar42));
      fVar43 = (float)((int)fVar45 * (uint)(fVar43 < fVar45) |
                      (int)fVar43 * (uint)(fVar43 >= fVar45));
      fVar39 = (float)((int)fVar45 * (uint)(fVar45 < fVar39) |
                      (int)fVar39 * (uint)(fVar45 >= fVar39));
    } while (lVar10 < *(short *)(iVar36 + 8));
  }
  if (DAT_00340470 == 0) {
    fVar43 = fVar43 - fVar39;
  }
  else {
    lVar10 = (long)*(short *)(DAT_00340470 + 8);
    if (lVar10 < 1) {
      fVar43 = fVar43 - fVar39;
    }
    else {
      iVar5 = *(int *)(DAT_00340470 + 0x30);
      do {
        fVar41 = *(float *)(iVar5 + 0xc);
        lVar10 = (long)((int)lVar10 + -1);
        fVar45 = *(float *)(iVar5 + 0x14);
        iVar5 = iVar5 + 0x24;
        fVar43 = (float)((int)fVar41 * (uint)(fVar43 < fVar41) |
                        (int)fVar43 * (uint)(fVar43 >= fVar41));
        fVar39 = (float)((int)fVar41 * (uint)(fVar41 < fVar39) |
                        (int)fVar39 * (uint)(fVar41 >= fVar39));
        fVar40 = (float)((int)fVar45 * (uint)(fVar40 < fVar45) |
                        (int)fVar40 * (uint)(fVar40 >= fVar45));
        fVar42 = (float)((int)fVar45 * (uint)(fVar45 < fVar42) |
                        (int)fVar42 * (uint)(fVar45 >= fVar42));
      } while (lVar10 != 0);
      fVar43 = fVar43 - fVar39;
    }
  }
  auVar18._8_8_ = uVar14;
  auVar18._0_8_ = 0x340320;
  DAT_00340460 = fVar42 - DAT_00340458 * 0.5;
  DAT_0034045c = fVar39 - DAT_00340458 * 0.5;
  DAT_00340440 = (int)(fVar43 / DAT_00340458) + 1;
  DAT_00340444 = (int)((fVar40 - fVar42) / DAT_00340458) + 1;
  DAT_0034043c = DAT_00340440 * DAT_00340444;
  FUN_00101730(auStack_2c0,0x100,0x253198,iStack_b4);
  lVar10 = FUN_00124cb8(*(undefined4 *)(auVar18._0_4_ + 0x188),auStack_2c0);
  *(undefined4 *)(auVar18._0_4_ + 0x154) = 0;
  *(int *)(auVar18._0_4_ + 0x19c) = (int)lVar10;
  if (lVar10 != -1) {
    uVar4 = FUN_001213d8(lVar10);
    *(undefined4 *)(auVar18._0_4_ + 0x154) = uVar4;
  }
  FUN_00101730(auStack_2c0,0x100,0x2531a8,iStack_b4);
  lVar10 = FUN_00124cb8(*(undefined4 *)(auVar18._0_4_ + 0x188),auStack_2c0);
  *(undefined4 *)(auVar18._0_4_ + 0x158) = 0;
  *(int *)(auVar18._0_4_ + 0x1a0) = (int)lVar10;
  if (lVar10 != -1) {
    uVar4 = FUN_001213d8(lVar10);
    *(undefined4 *)(auVar18._0_4_ + 0x158) = uVar4;
  }
  FUN_00101730(auStack_2c0,0x100,0x2531b8,iStack_b4);
  lVar10 = FUN_00124cb8(*(undefined4 *)(auVar18._0_4_ + 0x188),auStack_2c0);
  *(undefined4 *)(auVar18._0_4_ + 0x15c) = 0;
  *(int *)(auVar18._0_4_ + 0x1a4) = (int)lVar10;
  if (lVar10 != -1) {
    uVar4 = FUN_001213d8(lVar10);
    *(undefined4 *)(auVar18._0_4_ + 0x15c) = uVar4;
  }
  iVar5 = auVar18._0_4_;
  iVar36 = 0;
  lVar10 = 0;
  if (0 < *(short *)(*(int *)(iVar5 + 0x14c) + 8)) {
    auVar17._8_8_ = 0;
    auVar17._0_8_ = auVar18._8_8_;
    auVar18 = auVar17 << 0x40;
    do {
      lVar10 = (long)((int)lVar10 + 1);
      iVar7 = auVar18._0_4_;
      auVar18._0_8_ = (long)(iVar7 + 0x24);
      FUN_00121590(*(undefined4 *)(iVar7 + *(int *)(*(int *)(iVar5 + 0x14c) + 0x30)),0,&uStack_c0);
      uStack_c0 = uStack_c0 + 0xf & 0xfffffff0;
      iVar36 = iVar36 + uStack_c0;
    } while (lVar10 < *(short *)(*(int *)(iVar5 + 0x14c) + 8));
  }
  uVar12 = auVar18._8_8_;
  if (DAT_00340470 != 0) {
    lVar10 = 0;
    if (0 < *(short *)(DAT_00340470 + 8)) {
      auVar19._8_8_ = 0;
      auVar19._0_8_ = uVar12;
      auVar18 = auVar19 << 0x40;
      do {
        lVar10 = (long)((int)lVar10 + 1);
        iVar5 = auVar18._0_4_;
        auVar18._0_8_ = (long)(iVar5 + 0x24);
        FUN_00121590(*(undefined4 *)(iVar5 + *(int *)(DAT_00340470 + 0x30)),0,&uStack_c0);
        uStack_c0 = uStack_c0 + 0xf & 0xfffffff0;
        iVar36 = iVar36 + uStack_c0;
      } while (lVar10 < *(short *)(DAT_00340470 + 8));
    }
    uVar12 = auVar18._8_8_;
  }
  auVar52._8_8_ = uVar12;
  auVar52._0_8_ = 0x340320;
  uVar38 = (DAT_0034043c * 0xb + DAT_00340440 * DAT_00340444 + DAT_00340444) * 4 + 0xfU & 0xfffffff0
  ;
  iVar36 = FUN_0010d020(iVar36 + uVar38);
  iVar7 = auVar52._0_4_;
  iVar5 = *(int *)(iVar7 + 0x124);
  uVar32 = iVar36 + 0xfU & 0xfffffff0;
  *(uint *)(iVar7 + 0x108) = uVar32;
  DAT_00340424 = (int *)(uVar32 + iVar5 * 4);
  if (0 < iVar5) {
    iVar7 = *(int *)(iVar7 + 0x120);
    puVar35 = (undefined4 *)(iVar36 + 0xfU & 0xfffffff0);
    do {
      iVar5 = iVar5 + -1;
      *puVar35 = DAT_00340424;
      DAT_00340424 = DAT_00340424 + iVar7;
      puVar35 = puVar35 + 1;
    } while (iVar5 != 0);
  }
  iStack_b0 = 0;
  auVar20._0_8_ = (long)DAT_00340444;
  auVar20._8_8_ = in_a0_udw;
  uVar32 = (int)DAT_00340424 + DAT_0034043c * 0x2c + 0xf & 0xfffffff0;
  if (0 < auVar20._0_8_) {
    auVar21._8_8_ = 0;
    auVar21._0_8_ = auVar16._8_8_;
    auVar16 = auVar21 << 0x40;
    puVar35 = DAT_00340428;
    do {
      iVar5 = 0;
      piVar34 = (int *)*puVar35;
      if (0 < DAT_00340440) {
        auVar20._0_8_ = auVar16._0_8_;
        do {
          iVar5 = iVar5 + 1;
          auVar16._0_8_ = (long)(auVar16._0_4_ + 0x2c);
          iVar36 = auVar20._0_4_;
          *piVar34 = (int)DAT_00340424 + iVar36;
          piVar34 = piVar34 + 1;
          puVar8 = (undefined4 *)(iVar36 + (int)DAT_00340424);
          auVar20._0_8_ = (long)(iVar36 + 0x2c);
          *puVar8 = 0;
          puVar8[1] = 0;
          puVar8[3] = 0;
          iVar36 = DAT_00340440;
          puVar8[6] = 0;
          puVar8[7] = 0;
          puVar8[4] = 0;
          puVar8[5] = 0;
          puVar8[10] = 0;
          puVar8[9] = 0;
          puVar8[2] = 0;
          puVar8[8] = 0;
        } while (iVar5 < iVar36);
      }
      puVar35 = puVar35 + 1;
      iStack_b0 = iStack_b0 + 1;
    } while (iStack_b0 < DAT_00340444);
  }
  if (DAT_0034046c == 0) {
    if (DAT_00340470 != 0) goto LAB_0012dc8c;
  }
  else {
    lVar10 = 0;
    if (0 < *(short *)(DAT_0034046c + 8)) {
      iVar5 = 0;
      do {
        iVar36 = *(int *)(DAT_0034046c + 0x30) + iVar5;
        auVar52._0_8_ = (long)iVar36;
        iVar5 = iVar5 + 0x24;
        lVar11 = FUN_00131b68(*(undefined4 *)(iVar36 + 0xc),*(undefined4 *)(iVar36 + 0x14));
        if (lVar11 != 0) {
          *(int *)((int)lVar11 + 8) = auVar52._0_4_;
        }
        lVar10 = (long)((int)lVar10 + 1);
      } while (lVar10 < *(short *)(DAT_0034046c + 8));
    }
LAB_0012dc8c:
    auVar22._8_8_ = auVar16._8_8_;
    auVar22._0_8_ = 0x340000;
    if ((DAT_00340470 != 0) && (lVar10 = 0, 0 < *(short *)(DAT_00340470 + 8))) {
      iVar5 = 0;
      do {
        iVar36 = *(int *)(DAT_00340470 + 0x30) + iVar5;
        auVar52._0_8_ = (long)iVar36;
        iVar5 = iVar5 + 0x24;
        lVar11 = FUN_00131b68(*(undefined4 *)(iVar36 + 0xc),*(undefined4 *)(iVar36 + 0x14));
        if (lVar11 != 0) {
          *(int *)((int)lVar11 + 0xc) = auVar52._0_4_;
        }
        lVar10 = (long)((int)lVar10 + 1);
      } while (lVar10 < *(short *)(DAT_00340470 + 8));
      auVar22._0_8_ = 0x340000;
    }
    iStack_b0 = 0;
    iVar5 = auVar22._0_4_;
    auVar20._0_8_ = 0x340000;
    if (*(int *)(iVar5 + 0x444) < 1) goto LAB_0012de04;
    do {
      lVar10 = 0;
      if (0 < *(int *)(iVar5 + 0x440)) {
        do {
          auVar20._0_8_ = lVar10;
          lVar11 = (long)((int)lVar10 + 1);
          iVar36 = FUN_00131c10(lVar10,iStack_b0);
          uVar9 = auVar52._8_8_;
          lVar10 = (long)(int)*(undefined4 **)(iVar36 + 8);
          if (lVar10 != 0) {
            uVar14 = auVar20._8_8_;
            iVar7 = FUN_00121590(**(undefined4 **)(iVar36 + 8),uVar32);
            auVar20._0_8_ = (long)(iVar7 + 0x10);
            auVar20._8_8_ = uVar14;
            *(int *)(iVar36 + 8) = iVar7;
            iVar7 = (int)lVar10;
            uVar32 = uVar32 + uStack_c0 + 0xf & 0xfffffff0;
            FUN_00113aa8(*(undefined4 *)(iVar7 + 0x18),0,0,*(undefined4 *)(iVar7 + 0xc),
                         *(undefined4 *)(iVar7 + 0x10),*(undefined4 *)(iVar7 + 0x14),auVar20._0_8_);
          }
          auVar52._0_8_ = (long)(int)*(undefined4 **)(iVar36 + 0xc);
          auVar52._8_8_ = uVar9;
          if (auVar52._0_8_ != 0) {
            uVar9 = auVar20._8_8_;
            iVar7 = FUN_00121590(**(undefined4 **)(iVar36 + 0xc),uVar32,&uStack_c0);
            iVar51 = auVar52._0_4_;
            uVar4 = *(undefined4 *)(iVar51 + 0x14);
            *(int *)(iVar36 + 0xc) = iVar7;
            auVar20._0_8_ = (long)(iVar7 + 0x10);
            auVar20._8_8_ = uVar9;
            uVar32 = uVar32 + uStack_c0 + 0xf & 0xfffffff0;
            FUN_00113aa8(*(undefined4 *)(iVar51 + 0x18),0,0,*(undefined4 *)(iVar51 + 0xc),
                         *(undefined4 *)(iVar51 + 0x10),uVar4,auVar20._0_8_);
          }
          lVar10 = lVar11;
        } while (lVar11 < *(int *)(iVar5 + 0x440));
      }
      iStack_b0 = iStack_b0 + 1;
    } while (iStack_b0 < *(int *)(iVar5 + 0x444));
  }
  auVar20._0_8_ = 0x340000;
LAB_0012de04:
  iVar5 = auVar20._0_4_;
  *(undefined4 *)(iVar5 + 0x448) = 0;
  *(undefined4 *)(iVar5 + 0x44c) = 0;
  *(undefined4 *)(iVar5 + 0x450) = 0;
  fVar39 = DAT_00340464;
  if (*(int *)(iVar5 + 0x474) != 0) {
    iVar36 = 0;
    iStack_ac = 0;
    lVar10 = 0;
    iStack_a8 = 0;
    iStack_a4 = 0;
    if (0 < *(short *)(*(int *)(iVar5 + 0x474) + 8)) {
      iVar7 = 0;
      do {
        piVar34 = (int *)(*(int *)(*(int *)(iVar5 + 0x474) + 0x30) + iVar7);
        if ((piVar34[2] & 1U) == 0) {
          iVar51 = piVar34[3];
LAB_0012de74:
          uVar9 = FUN_00131b68(iVar51,piVar34[5]);
          uVar14 = auVar20._8_8_;
          auVar52._0_8_ = uVar9;
          FUN_00121590(*piVar34,0,&uStack_c0);
          auVar20._0_8_ = (long)piVar34[1];
          auVar20._8_8_ = uVar14;
          uStack_c0 = uStack_c0 + 0xf & 0xfffffff0;
          uVar12 = FUN_00132450(auVar20._0_8_);
          if (uVar12 == 2) {
            if (auVar52._0_8_ == 0) {
              uVar9 = FUN_00124e60(*piVar34);
              uVar14 = FUN_002094b0(-(float)piVar34[3]);
              uVar15 = FUN_002094b0(piVar34[5]);
              uVar13 = FUN_002094b0(*(undefined4 *)(iVar5 + 0x45c));
              fVar39 = *(float *)(iVar5 + 0x458);
              FUN_002094b0(*(float *)(iVar5 + 0x45c) + fVar39 * (float)*(int *)(iVar5 + 0x440));
              FUN_002094b0(*(undefined4 *)(iVar5 + 0x460));
              FUN_002094b0(*(float *)(iVar5 + 0x460) + fVar39 * (float)*(int *)(iVar5 + 0x444));
                    /* WARNING: Subroutine does not return */
              FUN_00105888(0x2530d0,0x462,0x2531c8,iStack_b4,uVar9,uVar14,uVar15,uVar13);
            }
            *(int *)(auVar52._0_4_ + 4) = *(int *)(auVar52._0_4_ + 4) + 1;
            iVar36 = iVar36 + uStack_c0;
            *(int *)(iVar5 + 0x44c) = *(int *)(iVar5 + 0x44c) + 1;
          }
          else if (uVar12 < 3) {
            if (uVar12 != 1) {
LAB_0012e104:
                    /* WARNING: Subroutine does not return */
              FUN_00105888(0x2530d0,0x499,0x253340);
            }
            *(int *)(iVar5 + 0x450) = *(int *)(iVar5 + 0x450) + 1;
            iStack_a8 = iStack_a8 + uStack_c0;
          }
          else {
            if (uVar12 != 3) goto LAB_0012e104;
            auVar20._0_8_ = (long)*piVar34;
            fVar39 = (float)FUN_00122218(auVar20._0_8_);
            if (fVar39 == 0.0) {
              iVar51 = *(int *)(iVar5 + 0x448);
            }
            else {
              if (fVar39 <= 768.0) {
                if (auVar52._0_8_ == 0) {
                  uVar9 = FUN_00124e60(*piVar34);
                  uVar14 = FUN_002094b0(-(float)piVar34[3]);
                  uVar15 = FUN_002094b0(piVar34[5]);
                  uVar13 = FUN_002094b0(*(undefined4 *)(iVar5 + 0x45c));
                  fVar39 = *(float *)(iVar5 + 0x458);
                  FUN_002094b0(*(float *)(iVar5 + 0x45c) + fVar39 * (float)*(int *)(iVar5 + 0x440));
                  FUN_002094b0(*(undefined4 *)(iVar5 + 0x460));
                  FUN_002094b0(*(float *)(iVar5 + 0x460) + fVar39 * (float)*(int *)(iVar5 + 0x444));
                    /* WARNING: Subroutine does not return */
                  FUN_00105888(0x2530d0,0x48a,0x253288,iStack_b4,uVar9,uVar14,uVar15,uVar13);
                }
                *auVar52._0_4_ = *auVar52._0_4_ + 1;
                iVar36 = iVar36 + uStack_c0;
                goto LAB_0012e110;
              }
              iVar51 = *(int *)(iVar5 + 0x448);
            }
            *(int *)(iVar5 + 0x448) = iVar51 + 1;
            iStack_ac = iStack_ac + uStack_c0;
          }
LAB_0012e110:
          iVar51 = *(int *)(iVar5 + 0x474);
        }
        else {
          if (*(int *)(iVar5 + 0x420) != 0) {
            iVar51 = piVar34[3];
            goto LAB_0012de74;
          }
          iVar51 = *(int *)(iVar5 + 0x474);
        }
        lVar10 = (long)((int)lVar10 + 1);
        iVar7 = iVar7 + 0x24;
      } while (lVar10 < *(short *)(iVar51 + 8));
    }
    uVar9 = auVar20._8_8_;
    if (0 < DAT_0034043c) {
      iVar5 = *DAT_00340424;
      iVar7 = DAT_0034043c;
      piVar34 = DAT_00340424;
      while( true ) {
        if (iVar5 != 0) {
          uVar38 = uVar38 + iVar5 * 4;
        }
        piVar30 = piVar34 + 1;
        piVar34 = piVar34 + 0xb;
        if (*piVar30 != 0) {
          uVar38 = uVar38 + *piVar30 * 4;
        }
        iVar7 = iVar7 + -1;
        if (iVar7 == 0) break;
        iVar5 = *piVar34;
      }
    }
    if ((DAT_00340478 != 0) && (iVar5 = 0, *(char *)(DAT_00340478 + 0x10) != '\0')) {
      do {
        iVar7 = iVar5 * 8;
        uVar15 = auVar52._8_8_;
        iVar5 = iVar5 + 1;
        uVar9 = auVar20._8_8_;
        uVar14 = FUN_00125a50(*(undefined4 *)(iVar7 + *(int *)(DAT_00340478 + 0x2c)));
        lVar10 = FUN_00124cb8(DAT_003404a8,uVar14);
        if (lVar10 == -1) {
                    /* WARNING: Subroutine does not return */
          FUN_00105888(0x2530d0,0x4cc,0x253368,uVar14);
        }
        iVar51 = FUN_0021b6e0(lVar10);
        iVar7 = *(int *)(iVar51 + 0x1c) + *(int *)(iVar7 + *(int *)(DAT_00340478 + 0x2c) + 4) * 0x68
        ;
        auVar52._0_8_ = (long)iVar7;
        auVar52._8_8_ = uVar15;
        if (*(int *)(iVar7 + 0x5c) == 0) {
                    /* WARNING: Subroutine does not return */
          FUN_00105888(0x2530d0,0x4d4,0x2533e8,uVar14);
        }
        fVar39 = (float)FUN_0011ea20(auVar52._0_8_);
        if (fVar39 < 0.01) {
          uVar4 = FUN_0011ea20(auVar52._0_8_);
          uVar9 = FUN_002094b0(uVar4);
                    /* WARNING: Subroutine does not return */
          FUN_00105888(0x2530d0,0x4da,0x253438,uVar14,uVar9);
        }
        FUN_00121590(lVar10,0,&uStack_c0);
        DAT_00340454 = DAT_00340454 + 1;
        uStack_c0 = uStack_c0 + 0xf & 0xfffffff0;
        iStack_a4 = iStack_a4 + uStack_c0;
        auVar20._0_8_ = (long)iStack_a4;
        auVar20._8_8_ = uVar9;
      } while (iVar5 < (int)(uint)*(byte *)(DAT_00340478 + 0x10));
    }
    puVar25 = &DAT_00340320;
    iVar5 = FUN_0010d020(iVar36 + (uVar38 + 0xf & 0xfffffff0));
    uVar32 = 0;
    *(int *)(puVar25 + 0x148) = iVar5;
    if (*(int *)(puVar25 + 0x128) != 0) {
      iVar7 = FUN_0010d020(iStack_ac + *(int *)(puVar25 + 0x128) * 4 + 0x10);
      iVar36 = *(int *)(puVar25 + 0x128);
      *(int *)(puVar25 + 0x10c) = iVar7;
      *(undefined4 *)(puVar25 + 0x128) = 0;
      uVar32 = iVar7 + iVar36 * 4 + 0xfU & 0xfffffff0;
    }
    uVar38 = 0;
    if (*(int *)(puVar25 + 0x134) != 0) {
      iVar7 = FUN_0010d020(iStack_a4 + *(int *)(puVar25 + 0x134) * 0x20 + 0x10);
      iVar36 = *(int *)(puVar25 + 0x134);
      *(int *)(puVar25 + 0x118) = iVar7;
      *(undefined4 *)(puVar25 + 0x134) = 0;
      uVar38 = iVar7 + iVar36 * 0x20 + 0xfU & 0xfffffff0;
    }
    uVar37 = 0;
    if (*(int *)(puVar25 + 0x130) != 0) {
      iVar7 = FUN_0010d020(iStack_a8 + *(int *)(puVar25 + 0x130) * 0x18 + 0x10);
      iVar36 = *(int *)(puVar25 + 0x130);
      *(undefined4 *)(puVar25 + 0x130) = 0;
      *(int *)(puVar25 + 0x114) = iVar7;
      uVar37 = iVar7 + iVar36 * 0x18 + 0xfU & 0xfffffff0;
    }
    iVar36 = 0;
    if (0 < *(int *)(puVar25 + 0x11c)) {
      piVar34 = *(int **)(puVar25 + 0x104);
      do {
        iVar7 = *piVar34;
        if (iVar7 != 0) {
          *piVar34 = 0;
          piVar34[4] = iVar5;
          iVar5 = iVar5 + iVar7 * 4;
        }
        iVar36 = iVar36 + 1;
        piVar34 = piVar34 + 0xb;
      } while (iVar36 < *(int *)(puVar25 + 0x11c));
    }
    uVar33 = iVar5 + 0xfU & 0xfffffff0;
    iVar5 = 0;
    piVar34 = DAT_00340424;
    if (0 < DAT_0034043c) {
      do {
        iVar36 = piVar34[1];
        if (iVar36 != 0) {
          piVar34[1] = 0;
          piVar34[5] = uVar33;
          uVar33 = uVar33 + iVar36 * 4;
        }
        iVar5 = iVar5 + 1;
        piVar34 = piVar34 + 0xb;
      } while (iVar5 < DAT_0034043c);
    }
    uVar33 = uVar33 + 0xf & 0xfffffff0;
    lVar10 = 0;
    if (0 < *(short *)(DAT_00340474 + 8)) {
      uVar14 = 0x340320;
      iVar5 = 0;
      do {
        iVar36 = (int)uVar14;
        puVar35 = (undefined4 *)(*(int *)(*(int *)(iVar36 + 0x154) + 0x30) + iVar5);
        if (((puVar35[2] & 1) == 0) || (*(int *)(iVar36 + 0x100) != 0)) {
          lVar11 = FUN_00132450(puVar35[1]);
          if (lVar11 == 2) {
            lVar11 = FUN_00131b68(puVar35[3],puVar35[5]);
            if (lVar11 != 0) {
              iVar36 = (int)lVar11;
              puVar8 = (undefined4 *)(*(int *)(iVar36 + 4) * 4 + *(int *)(iVar36 + 0x14));
              *(int *)(iVar36 + 4) = *(int *)(iVar36 + 4) + 1;
LAB_0012e608:
              *puVar8 = puVar35;
              goto LAB_0012e60c;
            }
            iVar36 = *(int *)((int)uVar14 + 0x154);
          }
          else if (lVar11 == 3) {
            fVar39 = (float)FUN_00122218(*puVar35);
            if (fVar39 == 0.0) {
              uVar4 = *puVar35;
            }
            else {
              if (fVar39 <= 768.0) {
                if (fVar39 == 0.0) {
                  iVar36 = *(int *)((int)uVar14 + 0x154);
                }
                else if (fVar39 <= 768.0) {
                  lVar11 = FUN_00131b68(puVar35[3],puVar35[5]);
                  if (lVar11 != 0) {
                    piVar34 = (int *)lVar11;
                    puVar8 = (undefined4 *)(*piVar34 * 4 + piVar34[4]);
                    *piVar34 = *piVar34 + 1;
                    goto LAB_0012e608;
                  }
                  iVar36 = *(int *)((int)uVar14 + 0x154);
                }
                else {
                  iVar36 = *(int *)((int)uVar14 + 0x154);
                }
                goto LAB_0012e610;
              }
              uVar4 = *puVar35;
            }
            iVar36 = FUN_00121590(uVar4,uVar32,&uStack_c0);
            fVar40 = (float)puVar35[6];
            fVar39 = (float)puVar35[7];
            uVar4 = puVar35[5];
            *(int *)(*(int *)((int)uVar14 + 0x128) * 4 + *(int *)((int)uVar14 + 0x10c)) = iVar36;
            uVar32 = uVar32 + uStack_c0 + 0xf & 0xfffffff0;
            FUN_00113aa8(-fVar40,-fVar39,puVar35[8],puVar35[3],puVar35[4],uVar4,iVar36 + 0x10);
            *(int *)((int)uVar14 + 0x128) = *(int *)((int)uVar14 + 0x128) + 1;
LAB_0012e60c:
            iVar36 = *(int *)((int)uVar14 + 0x154);
          }
          else {
            iVar36 = *(int *)((int)uVar14 + 0x154);
          }
        }
        else {
          iVar36 = *(int *)(iVar36 + 0x154);
        }
LAB_0012e610:
        lVar10 = (long)((int)lVar10 + 1);
        iVar5 = iVar5 + 0x24;
      } while (lVar10 < *(short *)(iVar36 + 8));
    }
    lVar10 = 0;
    if (0 < *(short *)(DAT_00340474 + 8)) {
      uVar14 = 0x340320;
      iVar36 = 0;
      iVar5 = DAT_00340474;
      while( true ) {
        puVar35 = (undefined4 *)(*(int *)(iVar5 + 0x30) + iVar36);
        iVar36 = iVar36 + 0x24;
        if (((puVar35[2] & 1) == 0) || (*(int *)((int)uVar14 + 0x100) != 0)) {
          lVar11 = FUN_00132450(puVar35[1]);
          if (lVar11 == 1) {
            iVar51 = (int)uVar14;
            iVar5 = *(int *)(iVar51 + 0x114);
            *(undefined4 *)(*(int *)(iVar51 + 0x130) * 0x18 + iVar5 + 8) =
                 *(undefined4 *)(iVar51 + 0x188);
            iVar7 = *(int *)(iVar51 + 0x130) * 0x18 + iVar5;
            *(uint *)(iVar7 + 8) = *(uint *)(iVar7 + 8) & 0xfff0ffff | 0xa0000;
            iVar5 = *(int *)(iVar51 + 0x130) * 0x18 + iVar5;
            *(uint *)(iVar5 + 8) =
                 *(uint *)(iVar5 + 8) & 0xffff0000 | (uint)*(ushort *)(puVar35 + 1);
            iVar5 = FUN_00121590(*puVar35,uVar37,&uStack_c0);
            fVar40 = (float)puVar35[6];
            fVar39 = (float)puVar35[7];
            uVar4 = puVar35[5];
            *(int *)(*(int *)((int)uVar14 + 0x130) * 0x18 + *(int *)((int)uVar14 + 0x114)) = iVar5;
            uVar37 = uVar37 + uStack_c0 + 0xf & 0xfffffff0;
            FUN_00113aa8(-fVar40,-fVar39,puVar35[8],puVar35[3],puVar35[4],uVar4,iVar5 + 0x10);
            iVar51 = (int)uVar14;
            iVar5 = *(int *)(iVar51 + 0x114);
            *(int *)(*(int *)(iVar51 + 0x130) * 0x18 + iVar5 + 4) = (int)lVar10;
            iVar7 = *(int *)(iVar51 + 0x130);
            *(int *)(iVar51 + 0x130) = iVar7 + 1;
            iVar7 = iVar7 * 0x18;
            *(undefined4 *)(iVar7 + iVar5 + 0x14) = 0;
            *(undefined4 *)(iVar7 + *(int *)(iVar51 + 0x114) + 0x10) = 0;
            *(undefined4 *)(iVar7 + *(int *)(iVar51 + 0x114) + 0xc) = 0;
          }
          iVar5 = *(int *)((int)uVar14 + 0x154);
        }
        else {
          iVar5 = *(int *)((int)uVar14 + 0x154);
        }
        lVar10 = (long)((int)lVar10 + 1);
        if (*(short *)(iVar5 + 8) <= lVar10) break;
        iVar5 = *(int *)((int)uVar14 + 0x154);
      }
    }
    auVar23._8_8_ = uVar9;
    auVar23._0_8_ = 0x340000;
    if ((DAT_00340478 != 0) && (iVar5 = 0, *(char *)(DAT_00340478 + 0x10) != '\0')) {
      do {
        iVar36 = iVar5 * 8;
        iVar5 = iVar5 + 1;
        uVar14 = auVar23._8_8_;
        uVar9 = FUN_00125a50(*(undefined4 *)(iVar36 + *(int *)(DAT_00340478 + 0x2c)));
        lVar10 = FUN_00124cb8(DAT_003404a8,uVar9);
        if (lVar10 == -1) {
                    /* WARNING: Subroutine does not return */
          FUN_00105888(0x2530d0,0x5dc,0x253368,uVar9);
        }
        iVar7 = FUN_0021b6e0(lVar10);
        lVar11 = (long)(*(int *)(iVar7 + 0x1c) +
                       *(int *)(iVar36 + *(int *)(DAT_00340478 + 0x2c) + 4) * 0x68);
        iVar51 = FUN_00121590(lVar10,uVar38,&uStack_c0);
        uVar38 = uVar38 + uStack_c0 + 0xf & 0xfffffff0;
        uVar4 = FUN_0012f3c0(uVar9);
        iVar7 = DAT_00340438;
        puVar35 = (undefined4 *)(DAT_00340454 * 0x20 + DAT_00340438);
        iVar36 = *(int *)((int)lVar11 + 0x58);
        *puVar35 = uVar4;
        puVar35[2] = 0;
        puVar35[1] = iVar51;
        puVar35[4] = (int)lVar11;
        if (iVar36 == -1) {
          puVar35[5] = 1;
          *(undefined4 *)(DAT_00340454 * 0x20 + iVar7 + 0x18) = 1;
          uVar12 = *(ulong *)(iVar51 + 0x60) | 1;
        }
        else {
          puVar35[5] = 0;
          *(undefined4 *)(DAT_00340454 * 0x20 + iVar7 + 0x18) = 0;
          uVar12 = *(ulong *)(iVar51 + 0x60) & 0xfffffffffffffffe;
        }
        *(ulong *)(iVar51 + 0x60) = uVar12;
        iVar36 = DAT_00340438;
        *(undefined4 *)(DAT_00340454 * 0x20 + DAT_00340438 + 0x1c) = 0;
        *(undefined4 *)(DAT_00340454 * 0x20 + iVar36 + 0xc) = 0x42700000;
        FUN_0011e8c0(lVar11,iVar51 + 0x10);
        auVar23._0_8_ = (long)DAT_00340478;
        auVar23._8_8_ = uVar14;
        DAT_00340454 = DAT_00340454 + 1;
      } while (iVar5 < (int)(uint)*(byte *)(DAT_00340478 + 0x10));
      auVar23._0_8_ = 0x340000;
    }
    iStack_b0 = 0;
    if (0 < *(int *)(auVar23._0_4_ + 0x444)) {
      do {
        uVar4 = DAT_0028f278;
        iVar5 = 0;
        if (0 < DAT_00340440) {
          iStack_a0 = iStack_b0 << 2;
          fVar39 = 1.1754945e-38;
          do {
            auStack_1c0._4_4_ = fVar39;
            auStack_1c0._0_4_ = uVar4;
            auStack_1b8._4_4_ = fVar39;
            auStack_1b8._0_4_ = uVar4;
            piVar34 = *(int **)(iVar5 * 4 + *(int *)(iStack_a0 + (int)DAT_00340428));
            bVar2 = piVar34[2] != 0;
            auStack_1b0._4_4_ = fVar39;
            auStack_1b0._0_4_ = uVar4;
            if (bVar2) {
              pfVar6 = (float *)FUN_00126a28(*(undefined4 *)(piVar34[2] + 4));
              fVar40 = *pfVar6;
              fVar42 = pfVar6[1];
              auStack_1c0._4_4_ =
                   (int)fVar42 * (uint)((float)auStack_1c0._4_4_ < fVar42) |
                   auStack_1c0._4_4_ * (uint)((float)auStack_1c0._4_4_ >= fVar42);
              auStack_1c0._0_4_ =
                   (int)fVar40 * (uint)(fVar40 < (float)auStack_1c0._0_4_) |
                   auStack_1c0._0_4_ * (uint)(fVar40 >= (float)auStack_1c0._0_4_);
              fVar42 = pfVar6[2];
              fVar40 = pfVar6[3];
              auStack_1b8._4_4_ =
                   (int)fVar40 * (uint)((float)auStack_1b8._4_4_ < fVar40) |
                   auStack_1b8._4_4_ * (uint)((float)auStack_1b8._4_4_ >= fVar40);
              auStack_1b8._0_4_ =
                   (int)fVar42 * (uint)(fVar42 < (float)auStack_1b8._0_4_) |
                   auStack_1b8._0_4_ * (uint)(fVar42 >= (float)auStack_1b8._0_4_);
              fVar42 = pfVar6[4];
              fVar40 = pfVar6[5];
              auStack_1b0._4_4_ =
                   (int)fVar40 * (uint)((float)auStack_1b0._4_4_ < fVar40) |
                   auStack_1b0._4_4_ * (uint)((float)auStack_1b0._4_4_ >= fVar40);
              auStack_1b0._0_4_ =
                   (int)fVar42 * (uint)(fVar42 < (float)auStack_1b0._0_4_) |
                   auStack_1b0._0_4_ * (uint)(fVar42 >= (float)auStack_1b0._0_4_);
            }
            iVar36 = 0;
            if (0 < *piVar34) {
              do {
                puVar35 = *(undefined4 **)(iVar36 * 4 + piVar34[4]);
                FUN_00131ae0(puVar35[3],puVar35[5],&iStack_bc,&iStack_b8);
                auVar18 = _pextlw(0,(long)(int)(DAT_0034045c + (float)iStack_bc * DAT_00340458 +
                                               DAT_00340458 * 0.5));
                lVar10 = (long)(int)(DAT_00340460 + (float)iStack_b8 * DAT_00340458 +
                                    DAT_00340458 * 0.5);
                auVar16 = _pextlw(0,lVar10);
                auVar16 = _pcpyld(auVar16,auVar18);
                lVar10 = FUN_00126a28(*puVar35,0,lVar10);
                if (lVar10 == 0) {
                  uVar9 = FUN_00124e60(*puVar35);
                  uVar14 = FUN_002094b0(-(float)puVar35[3]);
                  uVar15 = FUN_002094b0(puVar35[5]);
                    /* WARNING: Subroutine does not return */
                  FUN_00105888(0x2530d0,0x657,0x2534a8,iStack_b4,uVar9,uVar14,uVar15);
                }
                iVar7 = FUN_00121590(*puVar35,uVar33);
                fVar42 = (float)puVar35[6];
                fVar40 = (float)puVar35[7];
                *(int *)(iVar36 * 4 + piVar34[4]) = iVar7;
                uVar33 = uVar33 + uStack_c0 + 0xf & 0xfffffff0;
                FUN_00113aa8(-fVar42,-fVar40,puVar35[8],puVar35[3],puVar35[4],puVar35[5],
                             iVar7 + 0x10);
                auVar18 = _pextuw(in_zero_qw,auVar16);
                auVar17 = _prot3w(auVar16);
                lVar29 = 7;
                FUN_00113aa8(-(float)puVar35[6],-(float)puVar35[7],puVar35[8],
                             (float)puVar35[3] - auVar16._0_4_,(float)puVar35[4] - auVar17._0_4_,
                             (float)puVar35[5] - auVar18._0_4_,auStack_180);
                puVar1 = auStack_1a0 + 7;
                uVar32 = (uint)puVar1 & 7;
                *(ulong *)(puVar1 + -uVar32) =
                     *(ulong *)(puVar1 + -uVar32) & -1L << (uVar32 + 1) * 8 |
                     (ulong)auStack_1c0 >> (7 - uVar32) * 8;
                puVar1 = auStack_198 + 7;
                uVar32 = (uint)puVar1 & 7;
                *(ulong *)(puVar1 + -uVar32) =
                     *(ulong *)(puVar1 + -uVar32) & -1L << (uVar32 + 1) * 8 |
                     (ulong)auStack_1b8 >> (7 - uVar32) * 8;
                puVar1 = auStack_190 + 7;
                uVar32 = (uint)puVar1 & 7;
                *(ulong *)(puVar1 + -uVar32) =
                     *(ulong *)(puVar1 + -uVar32) & -1L << (uVar32 + 1) * 8 |
                     (ulong)auStack_1b0._0_8_ >> (7 - uVar32) * 8;
                pauVar31 = &auStack_140;
                piVar30 = (int *)lVar10;
                lVar10 = (long)piVar30[3];
                auVar17 = _pextlw(0x3f800000,(long)piVar30[5]);
                lVar11 = (long)piVar30[1];
                auVar23 = _pextlw(lVar10,lVar11);
                auVar52 = _pextlw(lVar10,(long)*piVar30);
                auVar22 = _pextlw((long)piVar30[2],(long)*piVar30);
                auVar21 = _pextlw((long)piVar30[2],lVar11);
                auVar16 = _pextlw(0x3f800000,(long)piVar30[4]);
                auVar19 = _pextlw(lVar10,lVar11);
                auVar18 = _por(in_zero_qw,auVar21);
                auVar24 = _pcpyld(auVar17,auVar18);
                auVar18 = _por(in_zero_qw,auVar52);
                auVar20 = _pcpyld(auVar17,auVar18);
                auVar18 = _por(in_zero_qw,auVar22);
                auVar18 = _pcpyld(auVar17,auVar18);
                auVar23 = _pcpyld(auVar17,auVar23);
                auVar17 = _pcpyld(auVar16,auVar19);
                auVar22 = _pcpyld(auVar16,auVar22);
                auVar19 = _pcpyld(auVar16,auVar21);
                auVar16 = _pcpyld(auVar16,auVar52);
                auStack_140._0_4_ = auVar22._0_4_;
                auStack_140._4_4_ = auVar22._4_4_;
                auStack_140._8_4_ = auVar22._8_4_;
                auStack_140._12_4_ = auVar22._12_4_;
                uStack_130 = auVar19._0_4_;
                uStack_12c = auVar19._4_4_;
                uStack_128 = auVar19._8_4_;
                uStack_124 = auVar19._12_4_;
                uStack_120 = auVar16._0_4_;
                uStack_11c = auVar16._4_4_;
                uStack_118 = auVar16._8_4_;
                uStack_114 = auVar16._12_4_;
                uStack_110 = auVar17._0_4_;
                uStack_10c = auVar17._4_4_;
                uStack_108 = auVar17._8_4_;
                uStack_104 = auVar17._12_4_;
                uStack_100 = auVar18._0_4_;
                uStack_fc = auVar18._4_4_;
                uStack_f8 = auVar18._8_4_;
                uStack_f4 = auVar18._12_4_;
                uStack_f0 = auVar24._0_4_;
                uStack_ec = auVar24._4_4_;
                uStack_e8 = auVar24._8_4_;
                uStack_e4 = auVar24._12_4_;
                uStack_e0 = auVar20._0_4_;
                uStack_dc = auVar20._4_4_;
                uStack_d8 = auVar20._8_4_;
                uStack_d4 = auVar20._12_4_;
                uStack_d0 = auVar23._0_4_;
                uStack_cc = auVar23._4_4_;
                uStack_c8 = auVar23._8_4_;
                uStack_c4 = auVar23._12_4_;
                auStack_1a0._0_4_ = auStack_1c0._0_4_;
                auStack_1a0._4_4_ = auStack_1c0._4_4_;
                auStack_198._0_4_ = auStack_1b8._0_4_;
                auStack_198._4_4_ = auStack_1b8._4_4_;
                auStack_190._0_4_ = (undefined4)auStack_1b0._0_8_;
                auStack_190._4_4_ = SUB84(auStack_1b0._0_8_,4);
                do {
                  auVar52 = _lqc2(*pauVar31);
                  auVar18 = _lqc2(auStack_180);
                  auVar19 = _lqc2(auStack_170);
                  auVar17 = _lqc2(auStack_160);
                  auVar16 = _lqc2(auStack_150);
                  _vmulabc(auVar18,auVar52);
                  _vmaddabc(auVar19,auVar52);
                  _vmaddabc(auVar17,auVar52);
                  auVar18 = _vmaddbc(auVar16,auVar52);
                  auVar16 = _qmfc2(auVar18._0_4_);
                  fVar40 = auVar16._0_4_;
                  auVar16 = _sqc2(auVar18);
                  *pauVar31 = auVar16;
                  if ((float)auStack_1a0._0_4_ < fVar40) {
                    fVar40 = (float)auStack_1a0._0_4_;
                  }
                  auVar16 = *pauVar31;
                  fVar42 = auVar16._0_4_;
                  if ((float)auStack_1a0._4_4_ <= fVar42) {
                    auVar16 = *pauVar31;
                    auStack_1a0._4_4_ = fVar42;
                  }
                  auVar16 = _prot3w(auVar16);
                  fVar42 = auVar16._0_4_;
                  if ((float)auStack_198._0_4_ < fVar42) {
                    fVar42 = (float)auStack_198._0_4_;
                  }
                  auVar16 = *pauVar31;
                  auVar18 = _prot3w(auVar16);
                  if ((float)auStack_198._4_4_ <= auVar18._0_4_) {
                    auVar16 = *pauVar31;
                    auStack_198._4_4_ = auVar18._0_4_;
                  }
                  auVar16 = _pextuw(in_zero_qw,auVar16);
                  fVar43 = auVar16._0_4_;
                  if ((float)auStack_190._0_4_ < fVar43) {
                    fVar43 = (float)auStack_190._0_4_;
                  }
                  auVar16 = _pextuw(in_zero_qw,*pauVar31);
                  fVar45 = auVar16._0_4_;
                  if (fVar45 < (float)auStack_190._4_4_) {
                    fVar45 = (float)auStack_190._4_4_;
                  }
                  lVar29 = (long)((int)lVar29 + -1);
                  pauVar31 = pauVar31 + 1;
                  auStack_190._4_4_ = fVar45;
                  auStack_190._0_4_ = fVar43;
                  auStack_198._0_4_ = fVar42;
                  auStack_1a0._0_4_ = fVar40;
                } while (-1 < lVar29);
                iVar36 = iVar36 + 1;
                uVar9 = auStack_190._0_8_;
                bVar2 = true;
                auVar3 = auStack_198;
                auStack_1c0 = auStack_1a0;
                iVar7 = *piVar34;
                uVar12 = auStack_190._0_8_;
                puVar1 = auStack_1c0 + 7;
                uVar32 = (uint)puVar1 & 7;
                *(ulong *)(puVar1 + -uVar32) =
                     *(ulong *)(puVar1 + -uVar32) & -1L << (uVar32 + 1) * 8 |
                     (ulong)auStack_1a0 >> (7 - uVar32) * 8;
                puVar1 = auStack_1b8 + 7;
                uVar32 = (uint)puVar1 & 7;
                *(ulong *)(puVar1 + -uVar32) =
                     *(ulong *)(puVar1 + -uVar32) & -1L << (uVar32 + 1) * 8 |
                     (ulong)auVar3 >> (7 - uVar32) * 8;
                auStack_1b8 = auVar3;
                puVar1 = auStack_1b0 + 7;
                uVar32 = (uint)puVar1 & 7;
                *(ulong *)(puVar1 + -uVar32) =
                     *(ulong *)(puVar1 + -uVar32) & -1L << (uVar32 + 1) * 8 |
                     (ulong)uVar9 >> (7 - uVar32) * 8;
                auStack_1b0._0_8_ = uVar9;
              } while (iVar36 < iVar7);
            }
            fVar40 = (float)auStack_1c0._4_4_;
            if (!bVar2) {
              auStack_1b8 = (undefined1  [8])0x0;
              auStack_1b0._4_4_ = DAT_00340458;
              auStack_1b0._0_4_ = -DAT_00340458;
              auStack_1c0._4_4_ = DAT_00340458;
              auStack_1c0._0_4_ = -DAT_00340458;
              fVar40 = DAT_00340458;
            }
            fVar40 = fVar40 * fVar40;
            fVar48 = (float)auStack_1c0._0_4_ * (float)auStack_1c0._0_4_;
            fVar41 = (float)auStack_1b0._4_4_ * (float)auStack_1b0._4_4_;
            fVar49 = (float)auStack_1b0._0_4_ * (float)auStack_1b0._0_4_;
            iVar5 = iVar5 + 1;
            fVar43 = fVar40 + (float)auStack_1b8._4_4_ * (float)auStack_1b8._4_4_;
            bVar2 = iVar5 < DAT_00340440;
            fVar45 = fVar40 + (float)auStack_1b8._0_4_ * (float)auStack_1b8._0_4_;
            fVar44 = fVar48 + (float)auStack_1b8._4_4_ * (float)auStack_1b8._4_4_;
            fVar47 = fVar48 + (float)auStack_1b8._0_4_ * (float)auStack_1b8._0_4_;
            fVar50 = fVar43 + fVar41;
            fVar43 = fVar43 + fVar49;
            fVar42 = fVar45 + fVar41;
            fVar45 = fVar45 + fVar49;
            fVar46 = fVar44 + fVar41;
            fVar43 = (float)((int)fVar43 * (uint)(fVar50 < fVar43) |
                            (int)fVar50 * (uint)(fVar50 >= fVar43));
            fVar50 = fVar40 + fVar41;
            fVar44 = fVar44 + fVar49;
            fVar42 = (float)((int)fVar42 * (uint)(fVar43 < fVar42) |
                            (int)fVar43 * (uint)(fVar43 >= fVar42));
            fVar40 = fVar40 + fVar49;
            fVar43 = (float)((int)fVar45 * (uint)(fVar42 < fVar45) |
                            (int)fVar42 * (uint)(fVar42 >= fVar45));
            fVar42 = fVar48 + fVar41;
            fVar43 = (float)((int)fVar46 * (uint)(fVar43 < fVar46) |
                            (int)fVar43 * (uint)(fVar43 >= fVar46));
            fVar41 = fVar47 + fVar41;
            fVar48 = fVar48 + fVar49;
            fVar43 = (float)((int)fVar44 * (uint)(fVar43 < fVar44) |
                            (int)fVar43 * (uint)(fVar43 >= fVar44));
            fVar47 = fVar47 + fVar49;
            fVar40 = (float)((int)fVar40 * (uint)(fVar50 < fVar40) |
                            (int)fVar50 * (uint)(fVar50 >= fVar40));
            fVar40 = (float)((int)fVar42 * (uint)(fVar40 < fVar42) |
                            (int)fVar40 * (uint)(fVar40 >= fVar42));
            fVar42 = (float)((int)fVar41 * (uint)(fVar43 < fVar41) |
                            (int)fVar43 * (uint)(fVar43 >= fVar41));
            piVar34[7] = (int)SQRT((float)((int)fVar48 * (uint)(fVar40 < fVar48) |
                                          (int)fVar40 * (uint)(fVar40 >= fVar48)));
            piVar34[6] = (int)SQRT((float)((int)fVar47 * (uint)(fVar42 < fVar47) |
                                          (int)fVar42 * (uint)(fVar42 >= fVar47)));
          } while (bVar2);
        }
        iStack_b0 = iStack_b0 + 1;
      } while (iStack_b0 < DAT_00340444);
    }
    fVar39 = 0.0;
    iStack_b0 = 0;
    if (0 < DAT_00340444) {
      do {
        iVar5 = 0;
        if (0 < DAT_00340440) {
          iStack_a0 = iStack_b0 << 2;
          do {
            iVar36 = *(int *)(iVar5 * 4 + *(int *)(iStack_a0 + (int)DAT_00340428));
            iVar7 = 0;
            if (0 < *(int *)(iVar36 + 4)) {
              do {
                iVar27 = iVar7 * 4;
                iVar7 = iVar7 + 1;
                puVar35 = *(undefined4 **)(iVar27 + *(int *)(iVar36 + 0x14));
                iVar51 = FUN_00121590(*puVar35,uVar33,&uStack_c0);
                uVar12 = *(ulong *)(iVar51 + 0x60);
                *(int *)(iVar27 + *(int *)(iVar36 + 0x14)) = iVar51;
                *(ulong *)(iVar51 + 0x60) = uVar12 | 0x400020;
                uVar33 = uVar33 + uStack_c0 + 0xf & 0xfffffff0;
                FUN_00113aa8(-(float)puVar35[6],-(float)puVar35[7],puVar35[8],puVar35[3],puVar35[4],
                             puVar35[5],iVar51 + 0x10);
                fVar40 = (float)FUN_00122218(*puVar35);
                fVar39 = (float)((int)fVar40 * (uint)(fVar39 < fVar40) |
                                (int)fVar39 * (uint)(fVar39 >= fVar40));
              } while (iVar7 < *(int *)(iVar36 + 4));
            }
            iVar5 = iVar5 + 1;
          } while (iVar5 < DAT_00340440);
        }
        iStack_b0 = iStack_b0 + 1;
      } while (iStack_b0 < DAT_00340444);
    }
    if (100.0 < fVar39) {
      pcVar28 = "oversubscribed distance tree";
      uVar9 = FUN_002094b0(fVar39);
                    /* WARNING: Subroutine does not return */
      FUN_00105888(pcVar28 + 0x30d0,0x6da,0x253520,uVar9,0x4059000000000000);
    }
  }
  DAT_00340464 = fVar39;
  FUN_0012f4f8();
  FUN_00130430(DAT_0034046c);
  FUN_0012f630();
  FUN_00130f90();
  FUN_00130da8();
  FUN_00130700();
  FUN_001326c8();
  FUN_0012fc30();
  FUN_00130190(iStack_b4);
  uRam0028f25c = 1;
  FUN_00130a38();
  return;
}


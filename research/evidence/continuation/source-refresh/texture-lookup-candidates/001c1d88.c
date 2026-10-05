
void FUN_001c1d88(undefined8 param_1)

{
  int iVar1;
  undefined1 in_zero_qw [16];
  undefined4 uVar2;
  undefined4 *puVar3;
  long lVar4;
  undefined8 uVar5;
  int *piVar6;
  undefined1 auVar7 [16];
  undefined1 auVar8 [16];
  undefined1 auVar9 [16];
  undefined1 auVar10 [16];
  char *pcVar11;
  undefined1 (*pauVar12) [16];
  undefined1 (*pauVar13) [16];
  int iVar14;
  undefined1 (*pauVar15) [16];
  float fVar16;
  float fVar17;
  undefined4 uVar18;
  undefined1 in_vf0 [16];
  undefined1 auVar19 [16];
  undefined1 auVar20 [16];
  undefined1 auStack_1b0 [16];
  undefined4 uStack_1a0;
  undefined4 uStack_19c;
  undefined4 uStack_198;
  undefined4 uStack_194;
  undefined4 uStack_190;
  undefined4 uStack_18c;
  undefined4 uStack_188;
  undefined4 uStack_184;
  undefined4 uStack_180;
  undefined4 uStack_17c;
  undefined4 uStack_178;
  undefined4 uStack_174;
  undefined1 auStack_170 [16];
  undefined4 uStack_120;
  undefined4 uStack_11c;
  int aiStack_110 [4];
  undefined1 auStack_100 [16];
  undefined1 auStack_f0 [16];
  undefined1 auStack_e0 [16];
  undefined1 auStack_d0 [16];
  undefined1 auStack_c0 [16];
  int iStack_b0;
  int iStack_ac;
  undefined *puStack_a8;
  int iStack_a4;
  undefined1 auStack_a0 [16];
  undefined1 auStack_90 [16];
  int iStack_80;
  
  pcVar11 = (char *)param_1;
  pauVar15 = (undefined1 (*) [16])(pcVar11 + 0x600);
  aiStack_110[0] = 0;
  auVar9 = _pextuw(in_zero_qw,*pauVar15);
  iStack_ac = FUN_00131c70(SUB164(*pauVar15,0),auVar9._0_4_,aiStack_110);
  if (*pcVar11 < '\0') {
    puStack_a8 = (undefined *)0x0;
  }
  else {
    puStack_a8 = &DAT_00241b40 + *pcVar11 * 0x150;
  }
  iStack_b0 = 0;
  fVar16 = (float)FUN_00126ae8(*(undefined4 *)(puStack_a8 + 0x14));
  if (0 < aiStack_110[0]) {
    iStack_80 = 0;
    iVar14 = iStack_ac;
    do {
      uStack_120 = *(undefined4 *)(iVar14 + 0x14);
      auVar10._8_8_ = auVar9._8_8_;
      auVar7 = _pextlw(0,(long)*(int *)(iVar14 + 4));
      uStack_11c = *(undefined4 *)(iVar14 + 0x18);
      auVar19 = _qmtc2(uStack_120);
      auVar9 = _pextlw(0,(long)*(int *)(iVar14 + 8));
      auVar8 = _pcpyld(auVar9,auVar7);
      auVar7 = _pextlw(0,(long)*(int *)(iVar14 + 0xc));
      auVar9 = _pextlw(0,(long)*(int *)(iVar14 + 0x10));
      auVar7 = _pcpyld(auVar9,auVar7);
      auVar9 = _pextuw(in_zero_qw,auVar7);
      uStack_1a0 = auVar7._0_4_;
      auVar20 = _qmtc2(uStack_1a0);
      uStack_180 = auVar8._0_4_;
      uStack_17c = auVar8._4_4_;
      uStack_178 = auVar8._8_4_;
      uStack_174 = auVar8._12_4_;
      auVar10._0_8_ = auVar7._0_8_;
      auVar8 = _vmulbc(auVar20,auVar19);
      auVar19 = _qmtc2(uStack_180);
      auVar8 = _vadd(auVar8,auVar19);
      auStack_170 = _sqc2(auVar8);
      uStack_19c = auVar7._4_4_;
      uStack_198 = auVar7._8_4_;
      uStack_194 = auVar7._12_4_;
      auVar8 = _pextlw(0,(long)(int)-auVar9._0_4_);
      auVar9 = _pextlw(0,auVar7._0_8_);
      auVar9 = _pcpyld(auVar9,auVar8);
      uStack_190 = auVar9._0_4_;
      uStack_18c = auVar9._4_4_;
      uStack_188 = auVar9._8_4_;
      uStack_184 = auVar9._12_4_;
      lVar4 = FUN_001c3618(fVar16 * 1.5,auStack_1b0,pauVar15,auStack_100,auStack_f0);
      if (lVar4 == 0) {
LAB_001c2230:
        auVar10._0_8_ = (long)iStack_b0;
      }
      else {
        auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x50));
        auVar7 = _lqc2(auStack_f0);
        auVar9 = _vmul(auVar9,auVar7);
        auVar9 = _vaddbc(auVar9,auVar9);
        auVar9 = _vaddbc(auVar9,auVar9);
        auVar9 = _qmfc2(auVar9._0_4_);
        _lqc2(auStack_100);
        auVar7 = _lqc2(*pauVar15);
        auVar7 = _vmove(auVar7);
        auStack_100 = _sqc2(auVar7);
        FUN_001c3920(0,auVar9._0_4_,param_1,pauVar15,auStack_100,0x20);
        pauVar12 = *(undefined1 (**) [16])(puStack_a8 + 0xe0);
        auVar10._0_8_ = (long)iStack_b0;
        if (pauVar12 != (undefined1 (*) [16])0x0) {
          pauVar13 = (undefined1 (*) [16])(pcVar11 + 0x30);
          uVar18 = 0;
          auVar7 = _qmtc2(1.0000999);
          auStack_90 = _sqc2(auVar7);
          auVar7._8_8_ = 0;
          auVar7._0_8_ = auVar9._8_8_;
          auVar8 = auVar7 << 0x40;
          auVar9 = _qmtc2(0);
          auStack_a0 = _sqc2(auVar9);
          iStack_a4 = iStack_80;
          do {
            auVar19 = _lqc2(*pauVar12);
            _vmove(auVar19);
            auVar20 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x40));
            auVar7 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x50));
            auVar9 = _lqc2(*pauVar13);
            _vmulabc(auVar9,auVar19);
            _vmaddabc(auVar20,auVar19);
            auVar7 = _vmaddbc(auVar7,auVar19);
            auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x600));
            auVar9 = _vadd(auVar7,auVar9);
            _sqc2(auVar7);
            auStack_e0 = _sqc2(auVar9);
            lVar4 = FUN_001c3618(*(undefined4 *)pauVar12[1],auStack_1b0,auStack_e0,auStack_100,
                                 auStack_f0);
            auVar8._0_8_ = (long)iStack_ac;
            if (lVar4 == 0) {
LAB_001c2224:
              pauVar12 = *(undefined1 (**) [16])(pauVar12[1] + 4);
            }
            else {
              lVar4 = FUN_00132110(iStack_ac + iStack_a4);
              uVar5 = auVar8._8_8_;
              if ((lVar4 == 2) || (auVar9 = _lqc2(auStack_f0), lVar4 == 4)) {
                fVar17 = (float)FUN_001151d8(*(undefined8 *)(pcVar11 + 0x650));
                auVar9 = _lqc2(auStack_f0);
                if (1.0 < fVar17) {
                  auVar10 = _lqc2(auStack_100);
                  auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x600));
                  _vmove(auVar10);
                  auVar8 = _vmove(auVar9);
                  auVar7 = _vsub(auVar8,auVar9);
                  _sqc2(auVar10);
                  auVar9 = _qmfc2(auVar7._0_4_);
                  _sqc2(auVar8);
                  auStack_d0 = _sqc2(auVar7);
                  uVar2 = FUN_00115998(pauVar13,auVar9._0_8_);
                  _qmtc2(uVar2);
                  auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x480));
                  auVar10 = _vmove(auVar9);
                  auVar8 = _lqc2(*pauVar13);
                  auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x50));
                  _vmove(auVar10);
                  auVar7 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x40));
                  _vmulabc(auVar8,auVar10);
                  _vmaddabc(auVar7,auVar10);
                  auVar7 = _vmaddbc(auVar9,auVar10);
                  auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x600));
                  auVar8 = _vadd(auVar7,auVar9);
                  auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x50));
                  auVar19 = _qmtc2(fVar17);
                  auVar9 = _vmulbc(auVar9,auVar19);
                  auStack_c0 = _sqc2(auVar9);
                  _sqc2(auVar10);
                  _sqc2(auVar7);
                  auStack_d0 = _sqc2(auVar8);
                  FUN_001375d8(auStack_d0,0,auStack_c0,0);
                  auVar9 = _lqc2(auStack_f0);
                }
              }
              auVar7 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x50));
              auVar9 = _vmul(auVar7,auVar9);
              auVar9 = _vaddbc(auVar9,auVar9);
              auVar9 = _vaddbc(auVar9,auVar9);
              auVar10 = _qmfc2(auVar9._0_4_);
              _lqc2(auStack_100);
              auVar9 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x600));
              auVar9 = _vmove(auVar9);
              auStack_100 = _sqc2(auVar9);
              FUN_001c3920(uVar18,auVar10._0_4_,param_1,pauVar15,auStack_100,2);
              auVar19 = _lqc2(*pauVar15);
              auVar7 = _lqc2(auStack_100);
              auVar9 = _lqc2(auStack_e0);
              auVar8 = _vsub(auVar7,auVar9);
              auVar9 = _qmtc2(*(undefined4 *)pauVar12[1]);
              auVar7 = _lqc2(auStack_f0);
              auVar7 = _vmulbc(auVar7,auVar9);
              auVar9 = _lqc2(auStack_a0);
              _vadd(auVar7,auVar8);
              auVar7 = _vaddbc(in_vf0,auVar9);
              auVar9 = _lqc2(auStack_90);
              auVar9 = _vmulbc(auVar7,auVar9);
              auVar9 = _vadd(auVar9,auVar19);
              auVar9 = _sqc2(auVar9);
              *pauVar15 = auVar9;
              FUN_001c2298(auStack_1b0,param_1,auStack_100,auStack_f0);
              auVar8._8_8_ = uVar5;
              auVar8._0_8_ = 3;
              puVar3 = (undefined4 *)(*(int *)(pcVar11 + 0x6f0) + 0x49c);
              do {
                auVar8._0_8_ = (long)(auVar8._0_4_ + -1);
                *puVar3 = 0;
                puVar3 = puVar3 + -0x4c;
              } while (-1 < auVar8._0_8_);
              piVar6 = *(int **)(pcVar11 + 8);
              if (*piVar6 == 4) {
                iVar1 = piVar6[1];
                auVar8._0_8_ = (long)iVar1;
                if (*(int *)(iVar1 + 300) == 4) {
                  auVar9 = _lqc2(auStack_f0);
                  if (*(int *)(iVar1 + 0xe0) != 0) {
                    auVar7 = _lqc2(*(undefined1 (*) [16])(pcVar11 + 0x650));
                    auVar9 = _vmul(auVar9,auVar7);
                    auVar9 = _vaddbc(auVar9,auVar9);
                    auVar9 = _vaddbc(auVar9,auVar9);
                    auVar8 = _qmfc2(auVar9._0_4_);
                    fVar17 = auVar8._0_4_ * 10.0;
                    if (2.0 < ABS(*(float *)(iVar1 + 0xec))) {
                      FUN_001c8f10(fVar17,fVar17,*(int *)(iVar1 + 0xe0),1);
                      piVar6 = *(int **)(pcVar11 + 8);
                    }
                  }
                  lVar4 = FUN_001b3e58(piVar6);
                  if (lVar4 == 0) {
                    FUN_00168e90();
                    piVar6 = *(int **)(pcVar11 + 8);
                  }
                  else {
                    piVar6 = *(int **)(pcVar11 + 8);
                  }
                }
                FUN_001a3240(piVar6,5);
                goto LAB_001c2224;
              }
              pauVar12 = *(undefined1 (**) [16])(pauVar12[1] + 4);
            }
          } while (pauVar12 != (undefined1 (*) [16])0x0);
          goto LAB_001c2230;
        }
      }
      iVar14 = iVar14 + 0x1c;
      iStack_b0 = auVar10._0_4_ + 1;
      auVar9._8_8_ = auVar10._8_8_;
      auVar9._0_8_ = (long)iStack_b0;
      iStack_80 = iStack_80 + 0x1c;
    } while (auVar9._0_8_ < aiStack_110[0]);
  }
  return;
}


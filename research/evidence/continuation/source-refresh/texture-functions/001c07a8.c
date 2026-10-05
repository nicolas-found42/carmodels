
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/physics/phy_coll.c:876 */

void FUN_001c07a8(undefined8 param_1)

{
  char cVar1;
  undefined4 uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  char cVar5;
  float fVar6;
  float *pfVar7;
  long lVar8;
  int iVar9;
  int *piVar10;
  int iVar11;
  uint uVar12;
  char *pcVar13;
  int iVar14;
  int iVar15;
  char *pcVar16;
  int iVar17;
  char *pcVar18;
  undefined *puVar19;
  float fVar20;
  float fVar21;
  float fVar22;
  float fVar23;
  float fVar24;
  float fVar25;
  undefined1 in_vf0 [16];
  undefined1 auVar26 [16];
  undefined1 auVar27 [16];
  undefined1 auVar28 [16];
  undefined1 auVar29 [16];
  undefined1 auVar30 [16];
  char acStack_a0 [16];
  undefined1 auStack_90 [16];
  int iStack_80;
  
  pcVar13 = acStack_a0;
  pcVar18 = acStack_a0;
  pcVar16 = (char *)param_1;
  if (*pcVar16 < '\0') {
    puVar19 = (undefined *)0x0;
    cVar5 = pcVar16[1];
  }
  else {
    puVar19 = &DAT_00241b40 + *pcVar16 * 0x150;
    cVar5 = pcVar16[1];
  }
  pcVar16[0x471] = '\0';
  iStack_80 = 0;
  iVar17 = 0;
  fVar25 = 0.0;
  cVar1 = pcVar16[1];
  if (cVar5 == '\x02') {
    iVar9 = 0;
    iVar14 = (byte)pcVar16[0x470] - 1;
  }
  else {
    iVar9 = 4;
    iVar14 = 0xb;
  }
  fVar21 = DAT_00290244;
  if (iVar14 < iVar9) {
    cVar5 = pcVar16[0x471];
  }
  else {
    iVar11 = iVar9 * 0x130 + *(int *)(pcVar16 + 0x6f0);
    do {
      acStack_a0[iVar9] = '\0';
      if (*(char *)(iVar11 + 5) != '\0') {
        auVar26 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x600));
        auVar27 = _lqc2(*(undefined1 (*) [16])(iVar11 + 0x60));
        auVar27 = _vadd(auVar26,auVar27);
        auVar26 = _lqc2(*(undefined1 (*) [16])(iVar11 + 0xb0));
        auVar27 = _vsub(auVar27,auVar26);
        auVar26 = _lqc2(*(undefined1 (*) [16])(iVar11 + 0x90));
        auVar26 = _vmul(auVar27,auVar26);
        auVar26 = _vaddbc(auVar26,auVar26);
        auVar26 = _vaddbc(auVar26,auVar26);
        auVar26 = _qmfc2(auVar26._0_4_);
        fVar24 = auVar26._0_4_;
        if (fVar24 < 0.0) {
          cVar5 = pcVar16[0x471];
          iVar15 = iVar9;
          if (fVar21 <= fVar24) {
            fVar24 = fVar21;
            iVar15 = iVar17;
          }
          acStack_a0[iVar9] = '\x01';
          pcVar16[0x471] = cVar5 + '\x01';
          fVar21 = fVar24;
          iVar17 = iVar15;
        }
      }
      iVar9 = iVar9 + 1;
      iVar11 = iVar11 + 0x130;
    } while (iVar9 <= iVar14);
    cVar5 = pcVar16[0x471];
  }
  if (cVar5 != '\0') {
    auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x600));
    auVar28 = _qmtc2(-fVar21);
    auVar26 = _lqc2(*(undefined1 (*) [16])(iVar17 * 0x130 + *(int *)(pcVar16 + 0x6f0) + 0x90));
    auVar26 = _vmulbc(auVar26,auVar28);
    auVar26 = _vadd(auVar26,auVar27);
    auVar26 = _sqc2(auVar26);
    *(undefined1 (*) [16])(pcVar16 + 0x600) = auVar26;
  }
  if (cVar1 == '\x05') {
    iVar17 = *(int *)(pcVar16 + 0x6f0);
    piVar10 = (int *)(puVar19 + 0xcc);
    iVar9 = 3;
    do {
      iVar14 = *(int *)(iVar17 + 0x120);
      iVar11 = *piVar10;
      piVar10 = piVar10 + 1;
      *(undefined4 *)(iVar14 + 0x80) = 0;
      *(undefined4 *)(iVar14 + 0x84) = 0;
      *(undefined4 *)(iVar14 + 0x88) = 0;
      *(undefined4 *)(iVar14 + 0x8c) = 0;
      auVar28 = _lqc2(*(undefined1 (*) [16])(iVar17 + 0x60));
      auVar29 = _lqc2(*(undefined1 (*) [16])(iVar17 + 0xb0));
      auVar26 = _lqc2(*(undefined1 (*) [16])(iVar17 + 0x90));
      iVar17 = iVar17 + 0x130;
      auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x600));
      auVar27 = _vadd(auVar27,auVar28);
      auVar27 = _vsub(auVar27,auVar29);
      auVar26 = _vmul(auVar27,auVar26);
      auVar26 = _vaddbc(auVar26,auVar26);
      auVar26 = _vaddbc(auVar26,auVar26);
      auVar26 = _qmfc2(auVar26._0_4_);
      if (auVar26._0_4_ <= *(float *)(iVar11 + 0x24)) {
        cVar5 = pcVar16[0x471];
        *pcVar13 = 1;
        pcVar16[0x471] = cVar5 + '\x01';
      }
      else {
        *pcVar13 = 0;
      }
      iVar9 = iVar9 + -1;
      pcVar13 = pcVar13 + 1;
    } while (-1 < iVar9);
    cVar5 = pcVar16[0x470];
  }
  else {
    cVar5 = pcVar16[0x470];
  }
  iVar17 = 0;
  uVar12 = 0;
  if (cVar5 != '\0') {
    iVar9 = 0;
    do {
      iVar17 = iVar17 + 1;
      *(undefined1 *)(iVar9 + *(int *)(pcVar16 + 0x6f0) + 0x80) = 0;
      uVar12 = (uint)(byte)pcVar16[0x470];
      iVar9 = iVar9 + 0x130;
    } while (iVar17 < (int)uVar12);
  }
  iVar17 = 0;
  if (uVar12 != 0) {
    fVar21 = 1.0;
    fVar24 = 0.0;
    iVar9 = 0;
    do {
      piVar10 = (int *)(iVar9 + *(int *)(pcVar16 + 0x6f0));
      iVar14 = *piVar10;
      if (iVar14 == 1) {
        if (*pcVar18 != '\0') {
          auVar26 = _lqc2(*(undefined1 (*) [16])(piVar10 + 0x18));
          auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x5f0));
          _vopmula(auVar26,auVar27);
          auVar26 = _vopmsub(auVar27,auVar26);
          auVar26 = _vsub(auVar26,auVar26);
          auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x650));
          auVar26 = _vadd(auVar27,auVar26);
          auStack_90 = _sqc2(auVar26);
          FUN_001c0e38(param_1,piVar10,piVar10 + 0x18);
          iVar14 = iVar9 + *(int *)(pcVar16 + 0x6f0);
          auVar28 = _lqc2(auStack_90);
          auVar27 = _lqc2(*(undefined1 (*) [16])(iVar14 + 0x90));
          auVar26 = _vmul(auVar28,auVar27);
          auVar26 = _vaddbc(auVar26,auVar26);
          auVar26 = _vaddbc(auVar26,auVar26);
          auVar26 = _qmfc2(auVar26._0_4_);
          auVar26 = _qmtc2(-auVar26._0_4_);
          auVar26 = _vmulbc(auVar27,auVar26);
          auVar27 = _vadd(auVar26,auVar28);
          auVar28 = _qmtc2(*(undefined4 *)(iVar14 + 0x74));
          auVar26 = _vmulbc(in_vf0,in_vf0);
          auVar28 = _vmulbc(auVar27,auVar28);
          auVar26 = _vsub(auVar26,auVar28);
          _sqc2(auVar27);
          _sqc2(auVar28);
          auStack_90 = _sqc2(auVar26);
          FUN_001bfd60(FLOAT_002901cc * *(float *)(pcVar16 + 0xc),iVar14 + 0x60,auStack_90,0xc,
                       param_1);
          *(char *)(iVar9 + *(int *)(pcVar16 + 0x6f0) + 0x80) = *pcVar18;
          lVar8 = FUN_001bfde8();
          if (lVar8 != 5) {
            *(undefined4 *)(puVar19 + 0xf0) = 1;
            goto LAB_001c0ce8;
          }
          uVar12 = (uint)(byte)pcVar16[0x470];
        }
      }
      else {
        if (iVar14 != 2) {
                    /* WARNING: Subroutine does not return */
          FUN_00105888(0x282d00,0x36c,0x282d40,iVar14);
        }
        if (*pcVar18 == '\0') {
          iVar14 = piVar10[0x48];
          *(undefined4 *)(iVar14 + 0xd8) = 0;
          *(undefined4 *)(iVar14 + 0xa0) = 0;
          *(undefined4 *)(iVar14 + 0xa4) = 0;
          *(undefined4 *)(iVar14 + 0xa8) = 0;
          *(undefined4 *)(iVar14 + 0xac) = 0;
          *(undefined4 *)(iVar14 + 0x100) = 0;
          *(float *)(iVar14 + 0xfc) = fVar21;
          *(float *)(iVar14 + 0x104) = fVar21;
          *(float *)(iVar14 + 0x10c) = fVar21;
          *(float *)(iVar14 + 0x110) = fVar21;
          *(undefined4 *)(iVar14 + 0xdc) = 0;
        }
        else {
          auVar29 = _lqc2(*(undefined1 (*) [16])(piVar10 + 0x24));
          auVar26 = _lqc2(*(undefined1 (*) [16])(piVar10 + 0x18));
          auVar28 = _lqc2(*(undefined1 (*) [16])(piVar10 + 0x2c));
          auVar27 = _qmfc2(auVar29._0_4_);
          iVar14 = *(int *)(puVar19 + iVar17 * 4 + 0xcc);
          auVar30 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x600));
          auVar26 = _vadd(auVar30,auVar26);
          auVar26 = _vsub(auVar28,auVar26);
          auVar26 = _vmul(auVar26,auVar29);
          auVar26 = _vaddbc(auVar26,auVar26);
          auVar26 = _vaddbc(auVar26,auVar26);
          auVar26 = _qmfc2(auVar26._0_4_);
          fVar6 = (float)FUN_00115998(pcVar16 + 0x30,auVar27._0_8_);
          fVar6 = auVar26._0_4_ * (fVar21 - ABS(fVar6));
          if (fVar24 < fVar6) {
            iVar11 = 1;
            if (1 < iVar17) {
              iVar11 = 2;
            }
            fVar22 = *(float *)(iVar14 + 0x28) + *(float *)(iVar14 + 0x28);
            iVar14 = *(int *)(pcVar16 + 0x6f0);
            iVar11 = iVar11 * 4 +
                     *(int *)(*(int *)(*(int *)(*(int *)(pcVar16 + 8) + 4) + 0x14c) + 0x17c);
            fVar23 = *(float *)(*(int *)(iVar9 + iVar14 + 0x120) + 0x16c);
            fVar20 = (*(float *)(iVar11 + 0xc0) + fVar22) - fVar23;
            fVar23 = *(float *)(iVar11 + 0xb4) + fVar22 + fVar23;
            if (fVar20 <= fVar6) {
              fVar20 = (float)((int)fVar6 * (uint)(fVar6 < fVar23) |
                              (int)fVar23 * (uint)(fVar6 >= fVar23));
            }
            iVar11 = 4;
            fVar23 = fVar20 * FLOAT_002901cc;
            pfVar7 = (float *)(*(int *)(iVar9 + iVar14 + 0x120) + 0x158);
            do {
              iVar11 = iVar11 + -1;
              *pfVar7 = fVar23;
              pfVar7 = pfVar7 + 1;
            } while (-1 < iVar11);
          }
          else {
            iVar14 = *(int *)(pcVar16 + 0x6f0);
            fVar20 = fVar6;
          }
          fVar20 = fVar20 - fVar6;
          fVar6 = fVar25;
          iVar11 = iStack_80;
          if ((fVar24 < fVar20) && (fVar6 = fVar20, iVar11 = iVar17, fVar20 <= fVar25)) {
            fVar6 = fVar25;
            iVar11 = iStack_80;
          }
          iStack_80 = iVar11;
          FUN_001be798(param_1,iVar14 + iVar9);
          *(char *)(iVar9 + *(int *)(pcVar16 + 0x6f0) + 0x80) = *pcVar18;
          fVar25 = fVar6;
        }
LAB_001c0ce8:
        uVar12 = (uint)(byte)pcVar16[0x470];
      }
      iVar17 = iVar17 + 1;
      iVar9 = iVar9 + 0x130;
      pcVar18 = pcVar18 + 1;
    } while (iVar17 < (int)uVar12);
  }
  if (0.0 < fVar25) {
    iVar9 = 3;
    auVar30 = _qmtc2(fVar25);
    pcVar13 = pcVar16 + 0x660;
    auVar27 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x600));
    iVar17 = iStack_80 * 0x130 + *(int *)(pcVar16 + 0x6f0);
    auVar28 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x6a0));
    auVar29 = _lqc2(*(undefined1 (*) [16])(pcVar16 + 0x650));
    auVar26 = _lqc2(*(undefined1 (*) [16])(*(int *)(iVar17 + 0x120) + 0xc0));
    auVar26 = _vmulbc(auVar26,auVar30);
    auVar26 = _vadd(auVar26,auVar27);
    auVar26 = _sqc2(auVar26);
    *(undefined1 (*) [16])(pcVar16 + 0x600) = auVar26;
    auVar27 = _lqc2(*(undefined1 (*) [16])(iVar17 + 0x90));
    auVar26 = _vmul(auVar28,auVar27);
    auVar26 = _vaddbc(auVar26,auVar26);
    auVar26 = _vaddbc(auVar26,auVar26);
    auVar26 = _qmfc2(auVar26._0_4_);
    auVar26 = _qmtc2(-auVar26._0_4_);
    auVar26 = _vmulbc(auVar27,auVar26);
    auVar26 = _vadd(auVar26,auVar28);
    auVar26 = _sqc2(auVar26);
    *(undefined1 (*) [16])(pcVar16 + 0x6a0) = auVar26;
    auVar27 = _lqc2(*(undefined1 (*) [16])(iVar17 + 0x90));
    auVar26 = _vmul(auVar29,auVar27);
    auVar26 = _vaddbc(auVar26,auVar26);
    auVar26 = _vaddbc(auVar26,auVar26);
    auVar26 = _qmfc2(auVar26._0_4_);
    auVar26 = _qmtc2(-auVar26._0_4_);
    auVar26 = _vmulbc(auVar27,auVar26);
    auVar26 = _vadd(auVar26,auVar29);
    auVar26 = _sqc2(auVar26);
    *(undefined1 (*) [16])(pcVar16 + 0x650) = auVar26;
    do {
      uVar2 = *(undefined4 *)(pcVar16 + 0x6a4);
      uVar3 = *(undefined4 *)(pcVar16 + 0x6a8);
      uVar4 = *(undefined4 *)(pcVar16 + 0x6ac);
      iVar9 = iVar9 + -1;
      *(undefined4 *)(pcVar13 + 0x50) = *(undefined4 *)(pcVar16 + 0x6a0);
      *(undefined4 *)(pcVar13 + 0x54) = uVar2;
      *(undefined4 *)(pcVar13 + 0x58) = uVar3;
      *(undefined4 *)(pcVar13 + 0x5c) = uVar4;
      uVar2 = *(undefined4 *)(pcVar16 + 0x654);
      uVar3 = *(undefined4 *)(pcVar16 + 0x658);
      uVar4 = *(undefined4 *)(pcVar16 + 0x65c);
      *(undefined4 *)pcVar13 = *(undefined4 *)(pcVar16 + 0x650);
      *(undefined4 *)(pcVar13 + 4) = uVar2;
      *(undefined4 *)(pcVar13 + 8) = uVar3;
      *(undefined4 *)(pcVar13 + 0xc) = uVar4;
      pcVar13 = pcVar13 + 0x10;
    } while (-1 < iVar9);
    lVar8 = FUN_001bfde8();
    if (lVar8 != 5) {
      *(undefined4 *)(puVar19 + 0x104) = 1;
    }
  }
  return;
}


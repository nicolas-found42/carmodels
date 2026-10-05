
/* WARNING: Removing unreachable block (ram,0x0013174c) */
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/track/trackini.c:3816 */

void FUN_00131298(float param_1)

{
  uint uVar1;
  undefined1 in_zero_qw [16];
  undefined1 auVar2 [16];
  undefined1 auVar3 [16];
  undefined1 auVar4 [16];
  int iVar5;
  int *piVar6;
  uint *puVar7;
  int iVar8;
  undefined8 uVar9;
  undefined1 in_s1_qw [16];
  undefined1 auVar10 [16];
  ulong uVar11;
  undefined1 in_s2_qw [16];
  undefined1 auVar12 [16];
  int iVar13;
  undefined4 *puVar14;
  undefined1 in_s4_qw [16];
  undefined1 auVar16 [16];
  undefined1 auVar17 [16];
  undefined1 auVar18 [16];
  undefined1 auVar19 [16];
  float fVar20;
  float fVar21;
  float fVar22;
  undefined4 uStack_1c0;
  undefined4 uStack_1bc;
  undefined4 uStack_1b8;
  undefined4 uStack_1b4;
  undefined4 uStack_1b0;
  undefined4 uStack_1ac;
  undefined4 uStack_1a8;
  undefined4 uStack_1a4;
  undefined4 uStack_1a0;
  undefined4 uStack_19c;
  undefined4 uStack_198;
  undefined4 uStack_194;
  undefined4 uStack_190;
  undefined4 uStack_18c;
  undefined4 uStack_188;
  undefined4 uStack_184;
  undefined1 auStack_180 [64];
  undefined4 uStack_140;
  undefined4 uStack_13c;
  undefined4 uStack_138;
  undefined4 uStack_134;
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
  undefined1 auStack_100 [64];
  undefined4 uStack_c0;
  undefined4 uStack_bc;
  undefined4 uStack_b8;
  undefined4 uStack_b4;
  undefined4 uStack_b0;
  undefined4 uStack_ac;
  undefined4 uStack_a8;
  undefined4 uStack_a4;
  undefined4 uStack_a0;
  undefined4 uStack_9c;
  undefined4 uStack_98;
  undefined4 uStack_94;
  undefined4 uStack_90;
  undefined4 uStack_8c;
  undefined4 uStack_88;
  undefined4 uStack_84;
  undefined8 uVar15;
  
  uStack_b0 = in_s1_qw._0_4_;
  uStack_ac = in_s1_qw._4_4_;
  uStack_a8 = in_s1_qw._8_4_;
  uStack_a4 = in_s1_qw._12_4_;
  uStack_a0 = in_s2_qw._0_4_;
  uStack_9c = in_s2_qw._4_4_;
  uStack_98 = in_s2_qw._8_4_;
  uStack_94 = in_s2_qw._12_4_;
  uStack_90 = in_s4_qw._0_4_;
  uStack_8c = in_s4_qw._4_4_;
  uStack_88 = in_s4_qw._8_4_;
  uStack_84 = in_s4_qw._12_4_;
  if (iRam0028f25c != 0) {
    iVar13 = 0;
    if (0 < iRam0028f318) {
      puVar7 = &DAT_002353d0;
      auVar10 = _pextlw(0,0);
      auVar12 = _por(in_zero_qw,auVar10);
      auVar2 = _pextlw(0x3f800000,0);
      auVar3 = _pextlw(0,0x3f800000);
      auVar4 = _pextlw(0x3f800000,0);
      auVar2 = _pcpyld(auVar10,auVar2);
      auVar18 = _pextlw(0x3f000000,0x3f000000);
      auVar19 = _pcpyld(auVar3,auVar18);
      auVar17 = _pextlw(0xffffffffbf000000,0xffffffffbf000000);
      auVar18 = _por(in_zero_qw,auVar3);
      auVar18 = _pcpyld(auVar10,auVar18);
      fVar22 = -1.0;
      auVar16 = _por(in_zero_qw,auVar4);
      uStack_c0 = auVar2._0_4_;
      uStack_bc = auVar2._4_4_;
      uStack_b8 = auVar2._8_4_;
      uStack_b4 = auVar2._12_4_;
      auVar17 = _pcpyld(auVar3,auVar17);
      auVar3 = _pcpyld(auVar10,auVar16);
      auVar2 = _pcpyld(auVar4,auVar12);
      auVar4 = _por(in_zero_qw,auVar18);
      do {
        uVar1 = *puVar7;
        if (uVar1 == 2) {
          FUN_001154d0(puVar7 + 8);
          auVar12 = _pextlw((long)(int)puVar7[1],0);
          auVar12 = _pcpyld(auVar10,auVar12);
          puVar7[0x10] = auVar12._0_4_;
          puVar7[0x11] = auVar12._4_4_;
          puVar7[0x12] = auVar12._8_4_;
          puVar7[0x13] = auVar12._12_4_;
          fVar20 = (float)puVar7[1] - param_1 * 0.29999998;
          puVar7[1] = (uint)fVar20;
          if (fVar20 < fVar22) {
            do {
              fVar20 = (float)puVar7[1];
              puVar7[1] = (uint)(fVar20 + 1.0);
            } while (fVar20 + 1.0 < -1.0);
          }
        }
        else if (uVar1 < 3) {
          if (uVar1 != 1) {
LAB_001315ec:
                    /* WARNING: Subroutine does not return */
            FUN_00105888(0x2530d0,0xee8,0x253860,*puVar7);
          }
          FUN_001154d0(puVar7 + 8);
          auVar12 = _pextlw((long)(int)puVar7[1],0);
          auVar12 = _pcpyld(auVar10,auVar12);
          puVar7[0x10] = auVar12._0_4_;
          puVar7[0x11] = auVar12._4_4_;
          puVar7[0x12] = auVar12._8_4_;
          puVar7[0x13] = auVar12._12_4_;
          fVar20 = (float)puVar7[1] - param_1 * 0.59999996;
          puVar7[1] = (uint)fVar20;
          if (fVar20 < fVar22) {
            do {
              fVar20 = (float)puVar7[1];
              puVar7[1] = (uint)(fVar20 + 1.0);
            } while (fVar20 + 1.0 < -1.0);
          }
        }
        else if (uVar1 == 3) {
          FUN_001154d0(puVar7 + 8);
          fVar20 = (float)puVar7[1];
          fVar21 = fVar20 + param_1;
          puVar7[1] = (uint)fVar21;
          auVar12 = _pextlw(0,(long)(int)((float)(int)(fVar20 * 4.0) * 0.25));
          auVar12 = _pcpyld(auVar10,auVar12);
          puVar7[0x10] = auVar12._0_4_;
          puVar7[0x11] = auVar12._4_4_;
          puVar7[0x12] = auVar12._8_4_;
          puVar7[0x13] = auVar12._12_4_;
          while (1.0 < fVar21) {
            fVar21 = (float)puVar7[1] - 1.0;
            puVar7[1] = (uint)fVar21;
          }
        }
        else {
          if (uVar1 != 4) goto LAB_001315ec;
          uStack_1b0 = uStack_c0;
          uStack_1ac = uStack_bc;
          uStack_1a8 = uStack_b8;
          uStack_1a4 = uStack_b4;
          uStack_1c0 = auVar18._0_4_;
          uStack_1bc = auVar18._4_4_;
          uStack_1b8 = auVar18._8_4_;
          uStack_1b4 = auVar18._12_4_;
          uStack_1a0 = auVar17._0_4_;
          uStack_19c = auVar17._4_4_;
          uStack_198 = auVar17._8_4_;
          uStack_194 = auVar17._12_4_;
          uStack_190 = auVar2._0_4_;
          uStack_18c = auVar2._4_4_;
          uStack_188 = auVar2._8_4_;
          uStack_184 = auVar2._12_4_;
          FUN_00113aa8(0,0,((float)puVar7[1] + (float)puVar7[1]) * 3.1415925,0,0,0,auStack_180);
          FUN_00115560(auStack_100,&uStack_1c0,auStack_180);
          uStack_140 = auVar4._0_4_;
          uStack_13c = auVar4._4_4_;
          uStack_138 = auVar4._8_4_;
          uStack_134 = auVar4._12_4_;
          uStack_130 = auVar3._0_4_;
          uStack_12c = auVar3._4_4_;
          uStack_128 = auVar3._8_4_;
          uStack_124 = auVar3._12_4_;
          uStack_120 = auVar19._0_4_;
          uStack_11c = auVar19._4_4_;
          uStack_118 = auVar19._8_4_;
          uStack_114 = auVar19._12_4_;
          uStack_110 = auVar2._0_4_;
          uStack_10c = auVar2._4_4_;
          uStack_108 = auVar2._8_4_;
          uStack_104 = auVar2._12_4_;
          FUN_00115560(puVar7 + 8,auStack_100,&uStack_140);
          fVar20 = (float)puVar7[1] + param_1 * 5.0;
          puVar7[1] = (uint)fVar20;
          while (1.0 < fVar20) {
            fVar20 = (float)puVar7[1] - 1.0;
            puVar7[1] = (uint)fVar20;
          }
        }
        iVar13 = iVar13 + 1;
        puVar7 = puVar7 + 0x18;
      } while (iVar13 < iRam0028f318);
    }
    uVar15 = 0x340000;
    puVar14 = &DAT_00340000;
    iVar13 = 0;
    if (0 < DAT_00340454) {
      uVar9 = 0x340320;
      uVar11 = 0xfffffffffffffffe;
      iVar8 = DAT_00340438;
      while( true ) {
        iVar8 = iVar8 + iVar13 * 0x20;
        *(float *)(iVar8 + 0xc) = *(float *)(iVar8 + 0xc) + param_1;
        if ((*(int *)(iVar8 + 0x18) == 0) && (*(int *)(iVar8 + 0x14) == 0)) {
          iVar8 = *(int *)((int)uVar9 + 0x134);
        }
        else {
          *(float *)(iVar8 + 8) = *(float *)(iVar8 + 8) + param_1;
          fVar20 = (float)FUN_0011ea20(*(undefined4 *)(iVar8 + 0x10));
          fVar22 = *(float *)(iVar8 + 8);
          if (fVar20 < fVar22) {
            if (*(int *)(iVar8 + 0x14) == 0) {
              *(undefined4 *)(iVar8 + 8) = 0;
              *(undefined4 *)(iVar8 + 0x18) = 0;
              iVar5 = *(int *)(iVar8 + 4);
              *(ulong *)(iVar5 + 0x60) = *(ulong *)(iVar5 + 0x60) & uVar11;
              fVar22 = *(float *)(iVar8 + 8);
            }
            else if (fVar20 < 0.01) {
              *(undefined4 *)(iVar8 + 8) = 0;
              iVar5 = *(int *)(iVar8 + 4);
              fVar22 = *(float *)(iVar8 + 8);
            }
            else {
              while (fVar20 < fVar22) {
                fVar22 = (float)FUN_0011ea20(*(undefined4 *)(iVar8 + 0x10));
                fVar22 = *(float *)(iVar8 + 8) - fVar22;
                *(float *)(iVar8 + 8) = fVar22;
              }
              iVar5 = *(int *)(iVar8 + 4);
            }
          }
          else {
            iVar5 = *(int *)(iVar8 + 4);
          }
          FUN_0011e8c0(fVar22,*(undefined4 *)(iVar8 + 0x10),iVar5 + 0x10);
          iVar8 = *(int *)((int)uVar9 + 0x134);
        }
        puVar14 = (undefined4 *)uVar15;
        iVar13 = iVar13 + 1;
        if (iVar8 <= iVar13) break;
        iVar8 = *(int *)((int)uVar9 + 0x118);
      }
    }
    piVar6 = &DAT_00340540;
    iVar13 = 0xf;
    do {
      if (*piVar6 != -1) {
        fVar22 = (float)piVar6[4];
        fVar20 = (float)piVar6[3] + param_1;
        piVar6[3] = (int)fVar20;
        if (fVar22 <= fVar20) {
          do {
            fVar20 = fVar20 - fVar22;
          } while (fVar22 <= fVar20);
          piVar6[3] = (int)fVar20;
          iVar8 = piVar6[5];
          piVar6[5] = iVar8 + 1;
          if (piVar6[2] <= iVar8 + 1) {
            piVar6[5] = 0;
          }
          if (piVar6[piVar6[5] + 6] != -1) {
            *(undefined4 *)(*piVar6 * 4 + *(int *)(piVar6[1] + 0xec)) =
                 *(undefined4 *)(piVar6[piVar6[5] + 6] * 4 + *(int *)(piVar6[1] + 0xec));
          }
        }
      }
      iVar13 = iVar13 + -1;
      piVar6 = piVar6 + 0xe;
    } while (-1 < iVar13);
    iVar13 = puVar14[0x125];
    if (0 < iVar13) {
      iVar8 = puVar14[0x127];
      do {
        fVar22 = *(float *)(iVar8 + 0xc) - param_1;
        *(float *)(iVar8 + 0xc) = fVar22;
        if (fVar22 < 0.0) {
          iRam0028efd0 = iRam0028efd0 * 0x41c64e6d + 0x3039;
          *(float *)(iVar8 + 0xc) =
               (float)(iRam0028efd0 >> 0x10 & 0x7fff) * 3.051851e-05 * 5.0 + 3.1;
        }
        iVar13 = iVar13 + -1;
        iVar8 = iVar8 + 0x10;
      } while (iVar13 != 0);
    }
  }
  return;
}



/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/database/db_setup.c:284, 649 */

void FUN_001d9b80(void)

{
  int iVar1;
  int iVar2;
  undefined8 uVar3;
  ulong uVar4;
  undefined8 uVar5;
  long lVar6;
  undefined1 auVar7 [16];
  undefined1 auVar8 [16];
  uint uVar9;
  long lVar10;
  int iVar11;
  int iVar12;
  undefined4 uVar13;
  float fVar14;
  float fVar15;
  undefined1 auStack_a0 [32];
  float afStack_80 [4];
  
  uVar9 = 0;
  lVar10 = 0;
  iVar11 = 0;
  uRam00290444 = FUN_00118bc8(0x289b28,0x150,0x1da658,0);
  uVar3 = FUN_001185c8(0x289b38,0,0x240680,0x13d);
  if (*(int *)((int)uVar3 + 4) == 0) {
    return;
  }
LAB_001d9c1c:
  while( true ) {
    uVar4 = FUN_00117b40(uVar3,2);
    if (uVar4 != 0xdc) break;
    uVar13 = FUN_00117cb8(uVar3);
    *(undefined4 *)(uVar9 + 0x94) = uVar13;
    uVar13 = FUN_00117cb8(uVar3);
    *(undefined4 *)(uVar9 + 0x98) = uVar13;
  }
  if (uVar4 < 0xdd) {
    if (uVar4 == 0x52) {
      uVar13 = FUN_00117cb8(uVar3);
      *(undefined4 *)(uVar9 + 100) = uVar13;
      uVar13 = FUN_00117cb8(uVar3);
      *(undefined4 *)(uVar9 + 0x68) = uVar13;
      goto LAB_001d9c1c;
    }
    if (uVar4 < 0x53) {
      if (uVar4 == 8) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x70) = uVar13;
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x74) = uVar13;
        goto LAB_001d9c1c;
      }
      if (uVar4 < 9) {
        if (uVar4 == 4) {
          fVar15 = 57.295776;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x58) = uVar13;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x5c) = uVar13;
          FUN_001ca0f0(lVar10,1,afStack_80);
          fVar14 = *(float *)(uVar9 + 0x58);
          afStack_80[0] = afStack_80[0] * fVar15;
          if (1.0 < ABS(afStack_80[0] - fVar14)) {
            FUN_001b9508(0x289ba0,lVar10);
            fVar14 = *(float *)(uVar9 + 0x58);
          }
          lVar6 = FUN_001c9908(fVar14 * 0.01745329,lVar10,1);
          if (lVar6 == 0) {
            FUN_001b9508(0x289be8,PTR_s_FRONT_SPOILER_0023a9fc);
          }
          FUN_001ca0f0(lVar10,8,afStack_80);
          fVar14 = *(float *)(uVar9 + 0x5c);
          afStack_80[0] = afStack_80[0] * fVar15;
          if (1.0 < ABS(afStack_80[0] - fVar14)) {
            FUN_001b9508(0x289c10,lVar10);
            fVar14 = *(float *)(uVar9 + 0x5c);
          }
          lVar6 = FUN_001c9908(fVar14 * 0.01745329,lVar10,8);
          if (lVar6 == 0) {
            FUN_001b9508(0x289be8,PTR_s_REAR_SPOILER_0023aa18);
          }
        }
        else {
          if (uVar4 != 7) goto LAB_001da21c;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x7c) = uVar13;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x80) = uVar13;
        }
        goto LAB_001d9c1c;
      }
      if (uVar4 == 0xd) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x50) = uVar13;
        goto LAB_001d9c1c;
      }
      if (uVar4 == 0xf) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x48) = uVar13;
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x4c) = uVar13;
        goto LAB_001d9c1c;
      }
    }
    else {
      if (uVar4 == 0x93) {
        FUN_00117e38(uVar3,auStack_a0,0x14);
        uVar5 = FUN_001da5e0(auStack_a0);
        FUN_001da270(uVar9,uVar5);
        goto LAB_001d9c1c;
      }
      if (uVar4 < 0x94) {
        if (uVar4 == 0x59) {
          uVar5 = FUN_00118cd0(uRam00290444,iVar11);
          FUN_00118d80(uVar5,uRam00290444,0);
          uVar9 = (int)uVar5 + 0x1fU & 0xfffffff0;
          FUN_00117e38(uVar3,uVar9,0x14);
          lVar10 = FUN_001d5f90(uVar9);
          iVar11 = iVar11 + 1;
          if (lVar10 == 0) {
                    /* WARNING: Subroutine does not return */
            FUN_00105888(0x289b48,0x11c,0x289b70,uVar9);
          }
        }
        else {
          if (uVar4 != 0x8c) goto LAB_001da21c;
          iVar1 = FUN_00117d18(uVar3);
          *(char *)(uVar9 + 0x14) = (char)iVar1;
          for (; iVar1 != 0; iVar1 = iVar1 + -1) {
            iVar2 = FUN_00117d18(uVar3);
            uVar13 = FUN_00117cb8(uVar3);
            *(undefined4 *)((iVar2 + 1) * 4 + uVar9 + 0x1c) = uVar13;
          }
        }
        goto LAB_001d9c1c;
      }
      if (uVar4 == 0x9a) {
        uVar13 = FUN_00117c58(uVar3,0x23a9d8,8);
        *(undefined4 *)(uVar9 + 0x120) = uVar13;
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x140) = uVar13;
        iVar1 = FUN_00117cb8(uVar3);
        iVar2 = FUN_00117cb8(uVar3);
        iVar12 = FUN_00117cb8(uVar3);
        auVar8 = _pextlw((long)iVar2,(long)iVar1);
        auVar7 = _pextlw(0,(long)iVar12);
        auVar7 = _pcpyld(auVar7,auVar8);
        *(int *)(uVar9 + 0x130) = auVar7._0_4_;
        *(int *)(uVar9 + 0x134) = auVar7._4_4_;
        *(int *)(uVar9 + 0x138) = auVar7._8_4_;
        *(int *)(uVar9 + 0x13c) = auVar7._12_4_;
        goto LAB_001d9c1c;
      }
      if (uVar4 == 0xc0) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x18) = uVar13;
        goto LAB_001d9c1c;
      }
    }
  }
  else {
    if (uVar4 == 0xe2) {
      uVar13 = FUN_00117cb8(uVar3);
      *(undefined4 *)(uVar9 + 0xa0) = uVar13;
      fVar14 = (float)FUN_00117cb8(uVar3);
      *(float *)(uVar9 + 0xa4) = fVar14;
      *(float *)(uVar9 + 0xb0) = 1.0 / fVar14;
      *(float *)(uVar9 + 0xac) = 1.0 / *(float *)(uVar9 + 0xa0);
      goto LAB_001d9c1c;
    }
    if (uVar4 < 0xe3) {
      if (uVar4 == 0xdf) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0xc4) = uVar13;
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 200) = uVar13;
        goto LAB_001d9c1c;
      }
      if (0xdf < uVar4) {
        if (uVar4 == 0xe0) {
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0xb8) = uVar13;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0xbc) = uVar13;
        }
        else {
          if (uVar4 != 0xe1) goto LAB_001da21c;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x88) = uVar13;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x8c) = uVar13;
        }
        goto LAB_001d9c1c;
      }
      if (uVar4 == 0xdd) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0xe8) = uVar13;
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0xec) = uVar13;
        goto LAB_001d9c1c;
      }
      if (uVar4 == 0xde) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0xdc) = uVar13;
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0xe0) = uVar13;
        goto LAB_001d9c1c;
      }
    }
    else {
      if (uVar4 == 0x13a) {
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x100) = uVar13;
        uVar13 = FUN_00117cb8(uVar3);
        *(undefined4 *)(uVar9 + 0x104) = uVar13;
        goto LAB_001d9c1c;
      }
      if (uVar4 < 0x13b) {
        if (uVar4 == 0xe3) {
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0xf4) = uVar13;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0xf8) = uVar13;
          goto LAB_001d9c1c;
        }
        if (uVar4 == 0xe4) {
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0xd0) = uVar13;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0xd4) = uVar13;
          goto LAB_001d9c1c;
        }
      }
      else {
        if (uVar4 == 0x13b) {
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x10c) = uVar13;
          uVar13 = FUN_00117cb8(uVar3);
          *(undefined4 *)(uVar9 + 0x110) = uVar13;
          goto LAB_001d9c1c;
        }
        if (uVar4 == 0xffffffffffffffea) {
          FUN_001186e0(uVar3);
          FUN_00118f40(uRam00290444,0);
          return;
        }
      }
    }
  }
LAB_001da21c:
                    /* WARNING: Subroutine does not return */
  FUN_00105888(0x289b48,0x289,0x289c58);
}


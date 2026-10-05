
void FUN_00196020(undefined8 param_1)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  int iVar5;
  bool bVar6;
  int iVar7;
  int iVar8;
  int *piVar9;
  int *piVar10;
  int iVar11;
  int iVar12;
  int iVar13;
  int iVar14;
  float fVar15;
  float fVar16;
  int iVar17;
  float fVar18;
  uint uVar19;
  float fVar20;
  float fVar21;
  float fVar22;
  float fVar23;
  float fVar24;
  float fVar25;
  float fVar26;
  
  piVar9 = (int *)param_1;
  iVar1 = piVar9[1];
  iVar7 = (**(code **)(&DAT_0023cfd8 + *piVar9 * 0x5c))(param_1,0x12);
  iVar14 = *(int *)(iVar7 + 4);
  iVar17 = *(int *)(iVar14 + 0x14c);
  fVar25 = *(float *)(iVar14 + 0xf4);
  iVar2 = *(int *)(iVar17 + 0x188);
  iVar3 = *(int *)(iVar14 + 0xe4);
  fVar18 = *(float *)(iVar14 + 0xec);
  fVar21 = fVar25 / *(float *)(iVar2 + 0x2c);
  iVar4 = *(int *)(iVar17 + 0x180);
  iVar5 = *(int *)(iVar14 + 0xe0);
  iVar17 = *(int *)(iVar17 + 0x17c);
  if (0.0 <= fVar21) {
    fVar21 = (float)((int)fVar21 * (uint)(fVar21 < 1.0) | (uint)(fVar21 >= 1.0) * 0x3f800000);
  }
  else {
    fVar21 = 0.0;
  }
  fVar26 = ABS(fVar18) / *(float *)(iVar14 + 0xf0);
  fVar24 = *(float *)(iVar5 + 0x90) *
           *(float *)(*(char *)(iVar17 + 0x14) * 4 + iVar17 + 0x14) * *(float *)(iVar17 + 0x20);
  fVar22 = fVar24 / *(float *)(iVar2 + 0x2c);
  if (0.0 <= fVar22) {
    fVar22 = (float)((int)fVar22 * (uint)(fVar22 < 1.0) | (uint)(fVar22 >= 1.0) * 0x3f800000);
  }
  else {
    fVar22 = 0.0;
  }
  fVar15 = *(float *)(iVar5 + 0x78);
  if (0.0 <= fVar15) {
    fVar15 = (float)((int)fVar15 * (uint)(fVar15 < 1.0) | (uint)(fVar15 >= 1.0) * 0x3f800000);
  }
  else {
    fVar15 = 0.0;
  }
  iVar14 = 1;
  do {
    fVar20 = 0.0;
    if ((*(uint *)(iVar3 + 0x60) & 1) != 1) {
      fVar20 = 0.0;
      iVar17 = *(int *)(iVar14 * 4 + *(int *)(iVar1 + 0xd0));
      goto LAB_00196538;
    }
    iVar12 = iVar14 * 4;
    fVar23 = 0.0;
    fVar16 = *(float *)(iVar12 + iVar4 + 4 + 0x70);
    if (fVar16 == 0.0) {
      iVar17 = *(int *)(iVar12 + *(int *)(iVar1 + 0xd0));
    }
    else {
      fVar16 = (float)*(int *)(iVar12 + *(int *)(iVar1 + 0xd0)) / fVar16;
      if (*(char *)(*(int *)(*(int *)(iVar7 + 4) + 0xe0) + 0x11) != '\0') {
        fVar16 = fVar16 * (float)((int)fVar15 * (uint)(0.95 < fVar15) |
                                 (uint)(0.95 >= fVar15) * (int)0.95);
      }
      fVar20 = fVar16 * *(float *)(iVar12 + iVar4 + 0xa0);
      iVar17 = (int)((float)(int)(fVar20 * fVar25) * *(float *)(iVar4 + 0x23c));
    }
    bVar6 = iVar17 < 100;
    switch(iVar14) {
    case 1:
      fVar23 = (float)FUN_001d7d80(fVar21,iVar4,iVar14);
      fVar20 = 0.5;
      if (0.5 < fVar15) {
        fVar20 = (fVar15 - 0.5) + (fVar15 - 0.5) + 0.5;
        if (0.0 <= fVar20) {
          fVar20 = (float)((int)fVar20 * (uint)(fVar20 < 1.0) | (uint)(fVar20 >= 1.0) * 0x3f800000);
          goto LAB_001964d0;
        }
        fVar20 = fVar23 * 0.0;
      }
      break;
    case 2:
      fVar23 = (float)FUN_001d7d80(fVar21,iVar4,iVar14);
      iVar12 = iVar4 + 0x1e8;
      goto LAB_00196370;
    case 3:
      fVar23 = (float)FUN_001d7d80(fVar21,iVar4,iVar14);
      iVar12 = iVar4 + 0x1fc;
      goto LAB_00196370;
    case 4:
      fVar23 = (float)FUN_001d7d80(fVar21,iVar4,iVar14);
      iVar12 = iVar4 + 0x210;
      goto LAB_00196370;
    case 5:
      fVar23 = (float)FUN_001d7d80(fVar21,iVar4,iVar14);
      iVar12 = iVar4 + 0x224;
LAB_00196370:
      fVar20 = (float)FUN_00195760(fVar15,iVar12,0);
      fVar23 = fVar23 * fVar20;
      iVar17 = (int)((float)iVar17 * *(float *)(iVar4 + 0x238));
      bVar6 = iVar17 < 100;
      goto LAB_0019653c;
    case 6:
      fVar23 = *(float *)(iVar2 + 0x34);
      fVar16 = (float)((int)fVar23 * (uint)(fVar25 < fVar23) |
                      (int)fVar25 * (uint)(fVar25 >= fVar23));
      fVar23 = fVar16 / *(float *)(iVar2 + 0x2c);
      if (0.0 <= fVar23) {
        uVar19 = (int)fVar23 * (uint)(fVar23 < 1.0) | (uint)(fVar23 >= 1.0) * 0x3f800000;
      }
      else {
        uVar19 = 0;
      }
      fVar23 = (float)FUN_001d7d80(uVar19,iVar4,iVar14);
      iVar17 = (int)((float)(int)((float)(int)(fVar20 * fVar16) * *(float *)(iVar4 + 0x23c)) *
                    *(float *)(iVar4 + 0x238));
      bVar6 = iVar17 < 100;
      goto LAB_0019653c;
    case 7:
      iVar17 = (int)(((float)iVar17 / *(float *)(iVar12 + iVar4 + 4 + 0x70)) *
                     *(float *)(iVar12 + iVar4 + 0xa0) * fVar24);
      fVar20 = (float)FUN_001d7d80(fVar22,iVar4,iVar14);
      fVar20 = fVar20 * fVar22;
      break;
    case 8:
      if (iVar5 != 0) {
        fVar23 = fVar15;
      }
      fVar20 = fVar23 * *(float *)(iVar4 + 0xec) * *(float *)(iVar5 + 0x30) * (1.0 - fVar21);
      break;
    case 9:
      if (iVar5 == 0) {
        fVar20 = *(float *)(iVar4 + 0xf0);
      }
      else {
        if (0.0 < *(float *)(iVar2 + 0x80)) {
          fVar23 = *(float *)(iVar5 + 0x54) / *(float *)(iVar2 + 0x80);
        }
        else {
          fVar23 = 0.0;
        }
        iVar17 = (int)(*(float *)(iVar5 + 0x50) * fRam0028e374 * fRam0028e378) + 0x5622;
        fVar20 = *(float *)(iVar4 + 0xf0);
      }
LAB_001964d0:
      fVar20 = fVar23 * fVar20;
      break;
    case 10:
      fVar20 = fVar26;
      if (iVar5 != 0) {
        fVar20 = fVar26 * (1.0 - *(float *)(iVar5 + 0xcc));
      }
      fVar20 = fVar20 * *(float *)(iVar4 + 0xf4);
      iVar17 = (int)(ABS(fVar18) * fRam0028e37c + 1.0) * 0x5622;
      break;
    default:
      goto LAB_0019653c;
    }
LAB_00196538:
    bVar6 = iVar17 < 100;
    fVar23 = fVar20;
LAB_0019653c:
    iVar13 = iVar14 * 4;
    iVar12 = 100;
    if ((!bVar6) && (iVar12 = iVar17, 50000 < iVar17)) {
      iVar12 = 50000;
    }
    uVar19 = 0;
    if (0.0 <= fVar23) {
      uVar19 = (int)fVar23 * (uint)(fVar23 < 1.0) | (uint)(fVar23 >= 1.0) * 0x3f800000;
    }
    iVar17 = piVar9[1];
    iVar11 = 0;
    if (0 < *(int *)(iVar17 + 0x9c)) {
      piVar10 = (int *)(iVar1 + 0xc0);
      do {
        if (*(int *)(iVar13 + *piVar10) == 0) {
          iVar8 = *(int *)(iVar17 + 0x9c);
        }
        else {
          uVar19 = FUN_001d5118(uVar19);
          FUN_00142208(uVar19,*(undefined4 *)(iVar13 + *piVar10));
          FUN_00142248(*(undefined4 *)(iVar13 + *piVar10),iVar12);
          iVar17 = piVar9[1];
          iVar8 = *(int *)(iVar17 + 0x9c);
        }
        iVar11 = iVar11 + 1;
        piVar10 = piVar10 + 1;
      } while (iVar11 < iVar8);
    }
    iVar14 = iVar14 + 1;
    if (10 < iVar14) {
      return;
    }
  } while( true );
}


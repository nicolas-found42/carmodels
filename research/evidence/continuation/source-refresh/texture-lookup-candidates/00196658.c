
void FUN_00196658(undefined8 param_1)

{
  int iVar1;
  int *piVar2;
  undefined4 uVar3;
  int iVar4;
  int iVar5;
  float *pfVar6;
  int iVar7;
  int *piVar8;
  int iVar9;
  int iVar10;
  int iVar11;
  int *piVar12;
  float fVar13;
  float fVar14;
  uint uVar15;
  float fVar16;
  float fVar17;
  uint uVar18;
  float fVar19;
  float afStack_120 [20];
  int aiStack_d0 [20];
  int iStack_80;
  
  piVar12 = (int *)param_1;
  iVar1 = piVar12[1];
  iVar4 = (**(code **)(&DAT_0023cfd8 + *piVar12 * 0x5c))(param_1,0x12);
  iVar4 = *(int *)(iVar4 + 4);
  fVar13 = *(float *)(iVar4 + 0xec);
  fVar19 = *(float *)(iVar4 + 0xf0);
  iStack_80 = *(int *)(iVar4 + 0xe4);
  fVar17 = ABS(fVar13) / fVar19;
  piVar2 = *(int **)(iVar4 + 0xe0);
  if (0.0 <= fVar17) {
    uVar18 = (int)fVar17 * (uint)(fVar17 < 1.0) | (uint)(fVar17 >= 1.0) * 0x3f800000;
  }
  else {
    uVar18 = 0;
  }
  uVar3 = *(undefined4 *)(*(int *)(iVar4 + 0x14c) + 0x198);
  FUN_0020c7fc(aiStack_d0,0,0x50);
  FUN_0020c7fc(afStack_120,0,0x50);
  iVar4 = *(int *)(*piVar2 + 0x6f0);
  iVar7 = 3;
  do {
    if (*(char *)(iVar4 + 0x80) != '\0') {
      iVar9 = *(int *)(iVar4 + 0x120);
      fVar16 = 0.0;
      fVar17 = *(float *)(iVar9 + 0xfc);
      iVar10 = *(int *)(&DAT_0036d750 + *(char *)(iVar4 + 6) * 4);
      pfVar6 = afStack_120 + iVar10;
      fVar14 = *pfVar6;
      fVar17 = (float)((int)fVar17 * (uint)(fVar14 < fVar17) |
                      (int)fVar14 * (uint)(fVar14 >= fVar17));
      *pfVar6 = fVar17;
      aiStack_d0[iVar10] = aiStack_d0[iVar10] + 1;
      fVar14 = *(float *)(iVar9 + 0x100) * 0.01;
      fVar17 = (float)((int)fVar14 * (uint)(fVar17 < fVar14) |
                      (int)fVar17 * (uint)(fVar17 >= fVar14));
      *pfVar6 = fVar17;
      if (0.0 <= fVar17) {
        fVar16 = (float)((int)fVar17 * (uint)(fVar17 < 1.0) | (uint)(fVar17 >= 1.0) * 0x3f800000);
      }
      *pfVar6 = fVar16;
    }
    iVar7 = iVar7 + -1;
    iVar4 = iVar4 + 0x130;
  } while (-1 < iVar7);
  iVar4 = 1;
  do {
    if ((*(uint *)(iStack_80 + 0x60) & 1) == 1) {
      iVar9 = iVar4 * 4;
      fVar17 = 0.0;
      iVar7 = *(int *)(iVar9 + *(int *)(iVar1 + 0xd4));
      switch(iVar4) {
      case 1:
      case 2:
      case 3:
      case 4:
      case 6:
      case 7:
      case 8:
      case 9:
        if ((float)aiStack_d0[*(int *)(&DAT_0036d708 + iVar9)] != 0.0) {
          fVar17 = (float)FUN_001db9f8(uVar18,uVar3,iVar4);
          goto LAB_00196990;
        }
        break;
      default:
        goto LAB_00196990;
      case 10:
      case 0xb:
      case 0xc:
      case 0xd:
      case 0xe:
      case 0xf:
      case 0x10:
        iVar10 = *(int *)(&DAT_0036d6c0 + iVar9);
        if (2.0 <= ABS((float)piVar2[0x32])) {
          pfVar6 = afStack_120 + iVar10;
          fVar17 = *pfVar6;
          if (fVar17 != 0.0) {
            if (0.0 <= fVar17) {
              *pfVar6 = (float)((int)fVar17 * (uint)(fVar17 < 1.0) |
                               (uint)(fVar17 >= 1.0) * 0x3f800000);
            }
            else {
              *pfVar6 = 0.0;
            }
            fVar17 = (float)FUN_001db9f8(afStack_120[iVar10],uVar3,iVar4);
            if (iVar4 == 0xe) {
              fVar14 = (ABS(fVar13) * 5.0) / fVar19;
              fVar17 = fVar17 * (float)((int)fVar14 * (uint)(fVar14 < 1.0) |
                                       (uint)(fVar14 >= 1.0) * 0x3f800000);
            }
            iVar7 = FUN_001db9c8(uVar3);
            iVar7 = (*(int *)(iVar9 + *(int *)(iVar1 + 0xd4)) -
                    (int)*(float *)(iVar9 + iVar7 + 0x44)) +
                    (int)(afStack_120[iVar10] * fRam0028e384);
            goto LAB_00196990;
          }
        }
      }
      fVar17 = 0.0;
    }
    else {
      fVar17 = 0.0;
      iVar7 = *(int *)(iVar4 * 4 + *(int *)(iVar1 + 0xd4));
LAB_00196990:
    }
    iVar10 = iVar4 * 4;
    iVar9 = 100;
    if ((99 < iVar7) && (iVar9 = iVar7, 50000 < iVar7)) {
      iVar9 = 50000;
    }
    uVar15 = 0;
    iVar7 = piVar12[1];
    if (0.0 <= fVar17) {
      uVar15 = (int)fVar17 * (uint)(fVar17 < 1.0) | (uint)(fVar17 >= 1.0) * 0x3f800000;
    }
    iVar11 = 0;
    if (0 < *(int *)(iVar7 + 0x9c)) {
      piVar8 = (int *)(iVar1 + 200);
      do {
        if (*(int *)(iVar10 + *piVar8) == 0) {
          iVar5 = *(int *)(iVar7 + 0x9c);
        }
        else {
          uVar15 = FUN_001d5118(uVar15);
          FUN_00142208(uVar15,*(undefined4 *)(iVar10 + *piVar8));
          FUN_00142248(*(undefined4 *)(iVar10 + *piVar8),iVar9);
          iVar7 = piVar12[1];
          iVar5 = *(int *)(iVar7 + 0x9c);
        }
        iVar11 = iVar11 + 1;
        piVar8 = piVar8 + 1;
      } while (iVar11 < iVar5);
    }
    iVar4 = iVar4 + 1;
    if (0x10 < iVar4) {
      return;
    }
  } while( true );
}


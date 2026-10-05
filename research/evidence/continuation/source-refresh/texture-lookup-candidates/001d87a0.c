
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/database/db_engin.c */

void FUN_001d87a0(void)

{
  undefined1 uVar1;
  undefined4 uVar2;
  long lVar3;
  ulong uVar4;
  undefined8 uVar5;
  int iVar6;
  float *pfVar7;
  int iVar8;
  uint uVar9;
  int iVar10;
  float fVar11;
  float fVar12;
  float fVar13;
  float fVar14;
  undefined1 auStack_90 [32];
  
  uVar9 = 0;
  iVar10 = 0;
  uRam002903e8 = FUN_00118bc8(0x289818,0xb0,0x1d8d38,0);
  lVar3 = FUN_001185c8(0x289828,0,0x240680,0x13d);
  if (lVar3 != 0) {
    while( true ) {
      while( true ) {
        while( true ) {
          while( true ) {
            while( true ) {
              while( true ) {
                while( true ) {
                  uVar4 = FUN_00117b40(lVar3,2);
                  if (uVar4 != 0x9f) break;
                  uVar2 = FUN_00117cb8(lVar3);
                  *(undefined4 *)(uVar9 + 0xa8) = uVar2;
                }
                if (0x9f < uVar4) break;
                if (uVar4 == 0x87) {
                  uVar2 = FUN_00117cb8(lVar3);
                  *(undefined4 *)(uVar9 + 0x88) = uVar2;
                }
                else if (uVar4 < 0x88) {
                  if (uVar4 == 0x47) {
                    uVar2 = FUN_00117cb8(lVar3);
                    *(undefined4 *)(uVar9 + 0x30) = uVar2;
                  }
                  else if (uVar4 < 0x48) {
                    if (uVar4 == 1) {
                      uVar2 = FUN_00117cb8(lVar3);
                      *(undefined4 *)(uVar9 + 0x8c) = uVar2;
                    }
                    else {
                      if (uVar4 != 0xb) goto LAB_001d8c58;
                      uVar2 = FUN_00117c58(lVar3,0x24b490,3);
                      *(undefined4 *)(uVar9 + 0x94) = uVar2;
                    }
                  }
                  else if (uVar4 == 0x7e) {
                    uVar2 = FUN_00117cb8(lVar3);
                    *(undefined4 *)(uVar9 + 0x1c) = uVar2;
                  }
                  else {
                    if (uVar4 != 0x86) goto LAB_001d8c58;
                    uVar2 = FUN_00117cb8(lVar3);
                    *(undefined4 *)(uVar9 + 0x84) = uVar2;
                  }
                }
                else if (uVar4 == 0x98) {
                  uVar1 = FUN_00117c58(lVar3,0x24b4a0,3);
                  *(undefined1 *)(uVar9 + 0x14) = uVar1;
                }
                else if (uVar4 < 0x99) {
                  if (uVar4 == 0x89) {
                    uVar2 = FUN_00117c58(lVar3,0x24b480,2);
                    *(undefined4 *)(uVar9 + 0xa4) = uVar2;
                  }
                  else {
                    if (uVar4 != 0x93) goto LAB_001d8c58;
                    FUN_00117e38(lVar3,auStack_90,0x14);
                    uVar5 = FUN_001d8cc0(auStack_90);
                    FUN_001d8d40(uVar9,uVar5);
                    *(int *)(uVar9 + 0x18) = (int)uVar5;
                  }
                }
                else if (uVar4 == 0x9c) {
                  uVar2 = FUN_00117cb8(lVar3);
                  *(undefined4 *)(uVar9 + 0x98) = uVar2;
                }
                else {
                  if (uVar4 != 0x9e) goto LAB_001d8c58;
                  uVar2 = FUN_00117cb8(lVar3);
                  *(undefined4 *)(uVar9 + 0xac) = uVar2;
                }
              }
              if (uVar4 != 0xe8) break;
              uVar2 = FUN_00117cb8(lVar3);
              *(undefined4 *)(uVar9 + 0x34) = uVar2;
            }
            if (0xe8 < uVar4) break;
            if (uVar4 == 0xb1) {
              uVar1 = FUN_00117d18(lVar3);
              *(undefined1 *)(uVar9 + 0x91) = uVar1;
            }
            else if (uVar4 < 0xb2) {
              if (uVar4 == 0xa1) {
                uVar2 = FUN_00117cb8(lVar3);
                *(undefined4 *)(uVar9 + 0x2c) = uVar2;
              }
              else {
                if (uVar4 != 0xa2) goto LAB_001d8c58;
                uVar2 = FUN_00117cb8(lVar3);
                *(undefined4 *)(uVar9 + 0x80) = uVar2;
              }
            }
            else if (uVar4 == 0xb2) {
              uVar1 = FUN_00117d18(lVar3);
              *(undefined1 *)(uVar9 + 0x90) = uVar1;
            }
            else {
              if (uVar4 != 0xc6) goto LAB_001d8c58;
              uVar2 = FUN_00117cb8(lVar3);
              *(undefined4 *)(uVar9 + 0x24) = uVar2;
            }
          }
          if (uVar4 != 0x12f) break;
          fVar13 = (float)FUN_00117cb8(lVar3);
          *(float *)(uVar9 + 0x9c) = fVar13;
          if (fVar13 == 0.0) {
            *(undefined4 *)(uVar9 + 0xa0) = 0x3f800000;
          }
          else {
            *(float *)(uVar9 + 0xa0) = 1.0 / fVar13;
          }
        }
        if (0x12f < uVar4) break;
        pfVar7 = (float *)(uVar9 + 0x38);
        if (uVar4 == 0xec) {
          FUN_0020c7fc(pfVar7,0,0x48);
          fVar13 = 0.0;
          iVar6 = (int)((*(float *)(uVar9 + 0x2c) + 250.0) * 0.0009999999) + 1;
          iVar8 = 0;
          if (0 < iVar6) {
            fVar14 = 0.00019040365;
            do {
              fVar11 = (float)FUN_00117cb8(lVar3);
              fVar12 = (float)FUN_00117cb8(lVar3);
              *pfVar7 = fVar12;
              fVar11 = fVar12 * fVar11 * fVar14;
              pfVar7 = pfVar7 + 1;
              if (fVar13 < fVar11) {
                *(float *)(uVar9 + 0x28) = (float)iVar8 * 1000.0;
                fVar13 = fVar11;
              }
              iVar8 = iVar8 + 1;
            } while (iVar8 < iVar6);
          }
        }
        else {
          if (uVar4 != 0xed) goto LAB_001d8c58;
          uVar2 = FUN_00117cb8(lVar3);
          *(undefined4 *)(uVar9 + 0x20) = uVar2;
        }
      }
      if (uVar4 != 0xffffffffffffffd4) break;
      uVar5 = FUN_00118cd0(uRam002903e8,iVar10);
      FUN_00118d80(uVar5,uRam002903e8,0);
      uVar9 = (int)uVar5 + 0x1fU & 0xfffffff0;
      FUN_00117e38(lVar3,uVar9,0x14);
      iVar10 = iVar10 + 1;
    }
    if (uVar4 != 0xffffffffffffffea) {
LAB_001d8c58:
                    /* WARNING: Subroutine does not return */
      FUN_00105888(0x289838,0x191,0x289860);
    }
    FUN_001186e0(lVar3);
    FUN_00118f40(uRam002903e8,0);
  }
  return;
}


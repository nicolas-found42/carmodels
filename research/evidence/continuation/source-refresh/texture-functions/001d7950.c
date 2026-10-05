
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/database/db_crsnd.c */

void FUN_001d7950(void)

{
  int iVar1;
  long lVar2;
  ulong uVar3;
  undefined8 uVar4;
  long lVar5;
  int iVar6;
  undefined4 *puVar7;
  int iVar8;
  uint uVar9;
  int iVar10;
  uint uVar11;
  int iVar12;
  undefined4 uVar13;
  undefined1 auStack_d0 [64];
  undefined1 auStack_90 [64];
  
  uVar11 = 0;
  iVar12 = 0;
  uRam002903b8 = FUN_00118bc8(0x2896b0,0x240,0x1d7e60,0);
  lVar2 = FUN_001185c8(0x2896c8,0,0x240680,0x13d);
  if (lVar2 == 0) {
    return;
  }
  while( true ) {
    while( true ) {
      while( true ) {
        while( true ) {
          while (uVar3 = FUN_00117b40(lVar2,2), uVar3 == 0x93) {
            FUN_00117e38(lVar2,auStack_d0,0x40);
            uVar4 = FUN_001d7de8(auStack_d0);
            FUN_001d7e68(uVar11,uVar4);
            *(int *)(uVar11 + 0x44) = (int)uVar4;
          }
          if (0x93 < uVar3) break;
          if (uVar3 == 0x7f) {
            uVar13 = FUN_00117cb8(lVar2);
            *(undefined4 *)(uVar11 + 0x238) = uVar13;
          }
          else if (uVar3 < 0x80) {
            if (uVar3 != 0x6c) goto LAB_001d7ce8;
            FUN_00117b40(lVar2,2);
            uVar9 = 1;
            iVar1 = FUN_00117c58(lVar2,0x23af78,5);
            puVar7 = (undefined4 *)(uVar11 + iVar1 * 0x14 + 0x1d8);
            do {
              uVar9 = uVar9 + 1;
              uVar13 = FUN_00117cb8(lVar2);
              *puVar7 = uVar13;
              puVar7 = puVar7 + 1;
            } while (uVar9 < 5);
          }
          else {
            if (uVar3 != 0x80) goto LAB_001d7ce8;
            uVar13 = FUN_00117cb8(lVar2);
            *(undefined4 *)(uVar11 + 0x23c) = uVar13;
          }
        }
        if (uVar3 != 0xce) break;
        uVar13 = FUN_00117c58(lVar2,0x24af68,0x20);
        *(undefined4 *)(uVar11 + 0x40) = uVar13;
      }
      if (0xce < uVar3) break;
      if (uVar3 != 0xc9) goto LAB_001d7ce8;
      FUN_00117b40(lVar2,2);
      iVar6 = uVar11 + 8;
      iVar1 = FUN_00117c58(lVar2,0x23b860,0xb);
      FUN_00117b40(lVar2,2);
      iVar10 = iVar1 * 4;
      uVar13 = FUN_00117c58(lVar2,0x24aaa0,0xce);
      *(undefined4 *)(iVar10 + iVar6 + 0x40) = uVar13;
      lVar5 = FUN_00117b40(lVar2,2);
      if (lVar5 == 0x84) {
        FUN_00117dd8(lVar2,auStack_90,0x40);
        lVar5 = FUN_00117b40(lVar2,2);
      }
      if (lVar5 == 0xcb) {
        iVar8 = 3;
        puVar7 = (undefined4 *)(iVar1 * 0x14 + iVar6 + 0xf4);
        do {
          iVar8 = iVar8 + -1;
          uVar13 = FUN_00117cb8(lVar2);
          *puVar7 = uVar13;
          puVar7 = puVar7 + 1;
        } while (-1 < iVar8);
        FUN_00117b40(lVar2,2);
      }
      else {
        iVar6 = iVar1 * 0x14 + iVar6;
        *(undefined4 *)(iVar6 + 0xf4) = 0;
        *(undefined4 *)(iVar6 + 0xf8) = 0;
        *(undefined4 *)(iVar6 + 0xfc) = 0x3f800000;
        *(undefined4 *)(iVar6 + 0x100) = 0x3f800000;
      }
      uVar13 = FUN_00117cb8(lVar2);
      *(undefined4 *)(iVar10 + uVar11 + 0x74) = uVar13;
      FUN_00117b40(lVar2,2);
      uVar13 = FUN_00117cb8(lVar2);
      *(undefined4 *)(iVar10 + uVar11 + 0xa0) = uVar13;
      FUN_00117b40(lVar2,2);
      uVar13 = FUN_00117cb8(lVar2);
      *(undefined4 *)(iVar10 + uVar11 + 0xcc) = uVar13;
    }
    if (uVar3 != 0xffffffffffffffd4) break;
    uVar4 = FUN_00118cd0(uRam002903b8,iVar12);
    FUN_00118d80(uVar4,uRam002903b8,0);
    uVar11 = (int)uVar4 + 0x1fU & 0xfffffff0;
    FUN_00117e38(lVar2,uVar11,0x40);
    *(undefined4 *)(uVar11 + 0x238) = 0x3f800000;
    *(undefined4 *)(uVar11 + 0x23c) = 0x3f800000;
    iVar12 = iVar12 + 1;
  }
  if (uVar3 == 0xffffffffffffffea) {
    FUN_001186e0(lVar2);
    FUN_00118f40(uRam002903b8,0);
    return;
  }
LAB_001d7ce8:
                    /* WARNING: Subroutine does not return */
  FUN_00105888(0x2896d8,0x10c,0x289700);
}


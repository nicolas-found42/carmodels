
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/system/ps2/asyncf.c:97 */

int FUN_00105480(undefined8 param_1,undefined4 param_2)

{
  long lVar1;
  int iVar2;
  int iVar3;
  
  if (*(int *)(iRam0028ec98 + 0x100) == 0) {
    iVar2 = 0;
  }
  else {
    iVar3 = 1;
    while ((iVar2 = -1, iVar3 < 0x20 &&
           (iVar2 = iVar3, *(int *)(iVar3 * 0x120 + iRam0028ec98 + 0x100) != 0))) {
      iVar3 = iVar3 + 1;
    }
  }
  if (iVar2 == -1) {
                    /* WARNING: Subroutine does not return */
    FUN_00105888(0x2501a8,0x61,0x2501c8,0x20);
  }
  iVar3 = iRam0028ec98 + iVar2 * 0x120;
  *(undefined4 *)(iVar3 + 0x100) = 1;
  *(undefined4 *)(iVar3 + 0x114) = param_2;
  *(undefined4 *)(iVar3 + 0x104) = 0;
  *(undefined4 *)(iVar3 + 0x108) = 0;
  *(undefined4 *)(iVar3 + 0x10c) = 0;
  *(undefined4 *)(iVar3 + 0x110) = 0;
  lVar1 = FUN_00107fb0();
  if (lVar1 == 0) {
    FUN_001077f0(iVar3,param_1,2);
  }
  else {
    FUN_001077f0(iVar3,param_1,3);
  }
  *(undefined4 *)(iVar3 + 0x118) = 0;
  *(int *)(iVar3 + 0x11c) = DAT_00290610;
  if (DAT_00290610 != 0) {
    *(int *)(DAT_00290610 + 0x118) = iVar3;
  }
  if (DAT_0029060c == 0) {
    DAT_0029060c = iVar3;
  }
  DAT_00290610 = iVar3;
  if (iVar3 == DAT_0029060c) {
    FUN_001057f0(iVar3);
  }
  return iVar3;
}


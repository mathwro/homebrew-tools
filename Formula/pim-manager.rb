class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.3/pim-manager_0.4.3_darwin_arm64.tar.gz"
      sha256 "edd6ca3fca2dc7aaa0840f4248d457643b7f632a769781ff8d50624bc44134a4"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.3/pim-manager_0.4.3_darwin_amd64.tar.gz"
      sha256 "8d5d0ec5644cf89c7d7c2cf696ddb98216f4de13d44ccbbdd1a9635da807b3fc"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.3/pim-manager_0.4.3_linux_arm64.tar.gz"
      sha256 "4cd6363fa468c82c1dc619e6486266628c616a21cabd3aa17199566f457c5b10"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.3/pim-manager_0.4.3_linux_amd64.tar.gz"
      sha256 "1e541e5df60ac43a50724614f60613d43529b575d2ae18720c9c61c0fdb9eb7e"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
